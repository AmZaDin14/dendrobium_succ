"""
Predict.py — End-to-end ensemble inference for RLSuccSite.

Runs both trained PPO models (ProtT5 + TPEMPPS_CCP) on new protein
fragments and produces a weighted ensemble prediction for each sample.

Usage:
    python Predict.py \
        --prott5_features_pt path/to/prott5_K_features.pt \
        --fragments_fasta path/to/fragments.fasta \
        --output predictions.csv

Inputs:
    --prott5_features_pt : torch.save'd dict with 'ids' (list[str]) and
                           'features' (Tensor, shape Nx1024)
    --fragments_fasta    : 33-residue fragments centered on each K
    --output             : CSV path for prediction results

Feature engineering and the CCP+TPEMPPS scalers are loaded from saved
artifacts without GPU, no CUDA fallback path anywhere.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import joblib
import tempfile
import argparse
import numpy as np
import torch
import pandas as pd
from multiprocessing import Pool
from sklearn.preprocessing import StandardScaler
from tensordict import TensorDict
from tensordict.nn import TensorDictModule
from torch import nn
from torch.distributions import OneHotCategorical
from torchrl.data import DiscreteTensorSpec
from torchrl.modules import ProbabilisticActor
import torch.nn.functional as F

# Feature extractors — each reads a FASTA of 33-mer fragments and
# returns a 2D numpy array (samples x feature_dim).
from Feature.CKSAAP import extract_cksAAP_from_fasta
from Feature.CTDC import extract_ctdc_from_fasta
from Feature.PAAC import extract_pse_aac_from_fasta
from Feature.TPEMPPS import ZccF_LiHua, ZccF_alltoK


# ── Globals ──────────────────────────────────────────────────────
device = torch.device("cpu")
BASE_DIR = Path(__file__).resolve().parent.parent

# Training-data FASTA paths used to fit the StandardScalers if no
# cached scaler pickles exist yet.
train_negative_fasta = BASE_DIR / 'Dataset/train/fasta/train_negative_sites.fasta'
train_positive_fasta = BASE_DIR / 'Dataset/train/fasta/train_positive_sites.fasta'


# ── Helpers ──────────────────────────────────────────────────────

def stream_fasta_batches(fasta_path, batch_size):
    """
    Generator that yields (ids, sequences) batches from a FASTA file.

    Each FASTA entry is parsed as a two-line record:
        >sequence_id|position
        33-character residue fragment

    Yields batches of up to *batch_size* records, avoiding loading the
    entire file into memory — important for large-scale inference.
    """
    batch_ids, batch_seqs = [], []
    with open(fasta_path, "r") as f:
        while True:
            title = f.readline().strip()
            if not title:
                break
            seq = f.readline().strip()

            batch_ids.append(title)
            batch_seqs.append(seq)

            if len(batch_seqs) == batch_size:
                yield batch_ids, batch_seqs
                batch_ids, batch_seqs = [], []

    if batch_seqs:
        yield batch_ids, batch_seqs


def process_chunk(args):
    """
    Worker function for multiprocessing pool.

    Writes a subset of sequences to a temporary FASTA file, then
    extracts both TPEMPPS (528-D) and CCP (462-D = CKSAAP+CTDC+PAAC)
    features in one pass. Returns the concatenated feature matrices
    back to the main process.

    Using temp files is necessary because each feature extractor reads
    directly from a file path rather than accepting in-memory sequences.
    """
    indices, seqs = args

    # Write chunk to a temp FASTA so feature extractors can read it.
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
        for i, s in enumerate(seqs):
            tmp.write(f">seq{i}\n{s}\n")
        tmp_path = tmp.name

    # Extract both feature sets from the same temp file.
    tpempps = np.hstack((ZccF_LiHua(tmp_path), ZccF_alltoK(tmp_path)))
    ccp = np.hstack((
        extract_cksAAP_from_fasta(tmp_path),
        extract_ctdc_from_fasta(tmp_path),
        extract_pse_aac_from_fasta(tmp_path)
    ))

    os.remove(tmp_path)
    return indices, tpempps, ccp


# ── CLI entry point ───────────────────────────────────────────────
def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Ensemble prediction (ProtT5 + TPEMPPS_CCP) on new, unseen 33-mer fragments."
    )
    parser.add_argument('--prott5_features_pt', required=True,
                        help="Path to .pt file with keys 'ids' (list[str]) and "
                             "'features' (Tensor, Nx1024) — the 16th-residue "
                             "ProtT5 embedding for each fragment")
    parser.add_argument('--fragments_fasta', required=True,
                        help="FASTA of 33-residue fragments centered on each lysine (K)")
    parser.add_argument('--output', required=True,
                        help="Path to write the prediction CSV")
    parser.add_argument('--num_workers', type=int, default=6,
                        help="Number of parallel worker processes for TPEMPPS+CCP extraction")
    parser.add_argument('--batch_size', type=int, default=2048,
                        help="Fragments per streaming batch before writing to disk")
    args = parser.parse_args()

    # ── 1. Load precomputed ProtT5 features ─────────────────────
    # The .pt file contains two keys:
    #   - 'ids':      list of sequence IDs, same order as the FASTA
    #   - 'features': 2D float Tensor (N x 1024) — the 16th residue
    #                 (centre of the 33-mer window) embedding from
    #                 the ProtT5-XL UniRef50 transformer.
    # These are generated offline by Feature/ProtT5_combined.py.
    print("Loading ProtT5 features...")
    data = torch.load(args.prott5_features_pt, map_location='cpu')
    sequence_ids = list(data['ids'])
    X_ProtT5_new = data['features'].cpu().numpy().astype(np.float32)

    # ── 2. Load or fit StandardScalers for the hand-crafted features ─
    # The TPEMPPS (528-D) and CCP (462-D) feature sets use different
    # numeric ranges and must be z-score normalised before inference.
    # Scalers are fit once on the full training set and cached as
    # joblib pickles to avoid recomputation on repeated runs.
    scaler_tpempps_path = BASE_DIR / "Models/scaler_tpempps.pkl"
    scaler_ccp_path = BASE_DIR / "Models/scaler_ccp.pkl"

    if scaler_tpempps_path.exists() and scaler_ccp_path.exists():
        # Use precomputed scalers from a previous training fit
        scaler_tpempps = joblib.load(scaler_tpempps_path)
        scaler_ccp = joblib.load(scaler_ccp_path)
    else:
        # First run: compute both scalers from the original training FASTA
        print("Fitting feature scalers from training data...")
        X_train_tpempps = np.vstack((
            np.hstack((ZccF_LiHua(train_negative_fasta), ZccF_alltoK(train_negative_fasta))),
            np.hstack((ZccF_LiHua(train_positive_fasta), ZccF_alltoK(train_positive_fasta)))
        ))
        X_train_ccp = np.vstack((
            np.hstack((
                extract_cksAAP_from_fasta(train_negative_fasta),
                extract_ctdc_from_fasta(train_negative_fasta),
                extract_pse_aac_from_fasta(train_negative_fasta)
            )),
            np.hstack((
                extract_cksAAP_from_fasta(train_positive_fasta),
                extract_ctdc_from_fasta(train_positive_fasta),
                extract_pse_aac_from_fasta(train_positive_fasta)
            ))
        ))

        scaler_tpempps = StandardScaler().fit(X_train_tpempps)
        scaler_ccp = StandardScaler().fit(X_train_ccp)

        # Cache for future runs
        joblib.dump(scaler_tpempps, scaler_tpempps_path)
        joblib.dump(scaler_ccp, scaler_ccp_path)

    # ── 3. Load both trained PPO models ──────────────────────────
    # Both models are simple MLPs: LazyLinear -> ReLU -> LazyLinear(2),
    # wrapped as a ProbabilisticActor that outputs a OneHotCategorical
    # distribution over the two classes (succinylated / not).
    # Model filenames encode validation metrics for traceability.

    # --- ProtT5 model: inputs are 1024-D transformer embeddings ---
    actor_net_ProtT5 = nn.Sequential(nn.LazyLinear(1024), nn.ReLU(), nn.LazyLinear(2)).to(device)
    policy_module_ProtT5 = ProbabilisticActor(
        module=TensorDictModule(actor_net_ProtT5, in_keys=['observation'], out_keys=['logits']),
        spec=DiscreteTensorSpec(2),
        in_keys=['logits'],
        distribution_class=OneHotCategorical,
        return_log_prob=True,
    ).to(device)

    policy_module_ProtT5.load_state_dict(torch.load(
        BASE_DIR / 'Models/ProtT5_N10_ACC7142_MCC3513_SN7191_SP7130.pth',
        map_location=device
    ))
    policy_module_ProtT5.eval()

    # --- TPEMPPS_CCP model: inputs are 990-D hand-crafted features ---
    # input_dim = 528 (TPEMPPS) + 462 (CCP) = 990
    input_dim = scaler_tpempps.mean_.shape[0] + scaler_ccp.mean_.shape[0]
    actor_net_ZccFCCP = nn.Sequential(nn.LazyLinear(input_dim), nn.ReLU(), nn.LazyLinear(2)).to(device)
    policy_module_ZccFCCP = ProbabilisticActor(
        module=TensorDictModule(actor_net_ZccFCCP, in_keys=['observation'], out_keys=['logits']),
        spec=DiscreteTensorSpec(2),
        in_keys=['logits'],
        distribution_class=OneHotCategorical,
        return_log_prob=True,
    ).to(device)

    policy_module_ZccFCCP.load_state_dict(torch.load(
        BASE_DIR / 'Models/TPEMPPS_CCP_ACC7083_MCC3307_SN6943_SP7116.pth',
        map_location=device
    ))
    policy_module_ZccFCCP.eval()

    # ── 4. Streaming ensemble prediction ─────────────────────────
    # The input FASTA is processed in streaming batches to keep memory
    # usage bounded.  Within each batch, the 33-mer sequences are
    # distributed across *num_workers* processes for parallel feature
    # extraction (the bottleneck).  Once features are assembled, both
    # models run inference on the full batch, and their logits are
    # averaged (50/50) before softmax for the final ensemble output.
    print("Streaming + parallel prediction...")

    predicted_labels = []
    positive_probabilities = []
    all_sequences = []

    idx_offset = 0

    pool = Pool(processes=args.num_workers)

    with torch.no_grad():
        for batch_ids, batch_seqs in stream_fasta_batches(args.fragments_fasta, args.batch_size):

            all_sequences.extend(batch_seqs)

            # Split batch into chunks for parallel feature extraction
            chunk_size = max(1, len(batch_seqs) // args.num_workers)
            chunks = []

            for i in range(0, len(batch_seqs), chunk_size):
                indices = list(range(idx_offset + i, idx_offset + i + len(batch_seqs[i:i+chunk_size])))
                seqs = batch_seqs[i:i+chunk_size]
                chunks.append((indices, seqs))

            # Run TPEMPPS + CCP extraction in parallel across workers
            results = pool.map(process_chunk, chunks)

            # Merge features, preserving chunk order
            tp_list, cc_list = [], []
            for indices, tp, cc in results:
                tp_list.append(tp)
                cc_list.append(cc)

            X_tpempps = np.vstack(tp_list)
            X_ccp = np.vstack(cc_list)

            # Standardise features using training-set statistics
            X_tpempps = scaler_tpempps.transform(X_tpempps)
            X_ccp = scaler_ccp.transform(X_ccp)

            # Concatenate hand-crafted features into a 990-D vector
            X_batch = np.hstack((X_tpempps, X_ccp)).astype(np.float32)
            X_prot_batch = X_ProtT5_new[idx_offset: idx_offset + len(batch_seqs)]

            # Convert to tensors and run ensemble inference
            X_prot_tensor = torch.tensor(X_prot_batch, device=device)
            X_hand_tensor = torch.tensor(X_batch, device=device)

            td1 = TensorDict({'observation': X_prot_tensor}, batch_size=[len(batch_seqs)])
            logits1 = policy_module_ProtT5(td1)['logits']

            td2 = TensorDict({'observation': X_hand_tensor}, batch_size=[len(batch_seqs)])
            logits2 = policy_module_ZccFCCP(td2)['logits']

            # 50/50 ensemble: average logits, then softmax
            avg_logits = (logits1 * 0.5) + (logits2 * 0.5)
            probs = F.softmax(avg_logits, dim=-1)

            positive_probabilities.extend(probs[:, 1].cpu().tolist())
            predicted_labels.extend(probs.argmax(dim=-1).cpu().tolist())

            idx_offset += len(batch_seqs)
            print(f"Processed {idx_offset} samples", end="\r")
    print()

    pool.close()
    pool.join()

    # ── 5. Write output CSV ──────────────────────────────────────
    # Columns:
    #   SequenceID          — fragment identifier (e.g. XP_123456.1|19)
    #   Sequence            — the 33-mer amino acid fragment
    #   PositiveProbability — [0,1] probability of succinylation
    #   PredictedLabel      — 0 (negative) or 1 (positive)
    df = pd.DataFrame({
        'SequenceID': sequence_ids,
        'Sequence': all_sequences,
        'PositiveProbability': positive_probabilities,
        'PredictedLabel': predicted_labels,
    })

    df.to_csv(args.output, index=False)
    print(f"Saved -> {args.output}")


if __name__ == '__main__':
    main()
