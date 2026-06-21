"""Self-contained wet-lab evaluation for RLSuccSite predictions.

Generates synthetic negative controls (1:1 same-protein K-sites) and computes
comprehensive metrics: precision, recall, F1, MCC, AUC-ROC, AUC-PR.

This replaces the RLSuccSite-NegCtrl package with a self-contained version
that doesn't depend on sibling directory paths.

Usage:
    from d_officinale_succ.evaluate import run_full_evaluation

    metrics = run_full_evaluation(
        predictions_csv="data/processed/full/predictions.csv",
        test_csv="data/wetlab/test.csv",
        protein_fasta="data/wetlab/protein.faa",
        output_dir="data/processed/evaluation",
    )
"""

import csv
import json
import random
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    matthews_corrcoef,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)


def parse_seq_id(seq_id: str) -> tuple[str, int]:
    """>XP_020679229.1|pos_150 -> (XP_020679229.1, 150)."""
    sid = seq_id.strip().lstrip(">")
    acc, pos = sid.split("|pos_")
    return acc, int(pos)


def load_predictions_index(predictions_csv: Path) -> dict[tuple[str, int], dict]:
    """{(refseq_acc, pos): prediction_row} from predictions CSV."""
    idx = {}
    with open(predictions_csv) as f:
        for r in csv.DictReader(f):
            acc, pos = parse_seq_id(r["SequenceID"])
            idx[(acc, pos)] = {
                "MatchedSequence": r["Sequence"],
                "PositiveProbability": float(r["PositiveProbability"]),
                "PredictedLabel": int(r["PredictedLabel"]),
            }
    return idx


def load_proteome_k_sites(proteome_fasta: Path) -> dict[str, list[int]]:
    """{refseq_acc: [1-indexed K positions]} from RefSeq protein.faa."""
    from Bio import SeqIO
    idx = {}
    for record in SeqIO.parse(str(proteome_fasta), "fasta"):
        seq = str(record.seq).upper()
        idx[record.id] = [i + 1 for i, aa in enumerate(seq) if aa == "K"]
    return idx


def parse_motif(raw: str) -> tuple[str, int]:
    """Parse ModifiedSequence from test.csv into searchable form."""
    s = raw.strip().strip("_").strip('"')
    s = s.replace("(ox)", "").replace("(ac)", "")
    left, right = s.split("(su)")
    peptide = left + right
    k_index = len(left) - 1
    return peptide, k_index


def load_test_sites(test_csv: Path) -> list[dict]:
    """Load test.csv ground truth (Feng et al wet-lab positives)."""
    entries = []
    with open(test_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            peptide, k_index = parse_motif(row["ModifiedSequence"])
            entries.append({
                "ProteinAccession": row["ProteinAccession"].strip().strip('"'),
                "Position": int(row["Position"].strip().strip('"')),
                "Peptide": peptide,
                "KIndex": k_index,
            })
    return entries


def map_test_to_refseq(
    test_sites: list[dict],
    predictions_idx: dict[tuple[str, int], dict],
    proteome_k_sites: dict[str, list[int]],
) -> list[dict]:
    """Map test sites to RefSeq accessions using peptide matching.

    Scans predictions for each test peptide (same approach as RLSuccSite/test.py).
    """
    mapped = []
    for site in test_sites:
        peptide = site["Peptide"]
        k_index = site["KIndex"]
        center = 16

        for (refseq_acc, pos), pred in predictions_idx.items():
            seq = pred["MatchedSequence"]
            start = center - k_index
            end = start + len(peptide)
            if start < 0 or end > len(seq):
                continue
            if seq[start:end] == peptide:
                mapped.append({
                    "comp_accession": site["ProteinAccession"],
                    "refseq_accession": refseq_acc,
                    "sibling_pos": pos,
                    "k_index_in_peptide": k_index,
                })
                break  # take first match
    return mapped


def build_negatives(
    positives: list[dict],
    proteome_k_sites: dict[str, list[int]],
    rng: random.Random,
) -> tuple[list[dict], list[dict]]:
    """Pair each positive with a same-protein K-site not in the positive set.

    Policy (from RLSuccSite-NegCtrl):
      - 1:1 ratio (one negative per positive)
      - Same-protein K-sites
      - Random selection
      - Drop positives whose protein has no other K
    """
    by_protein = {}
    for p in positives:
        by_protein.setdefault(p["refseq_accession"], []).append(p)

    kept, negs = [], []
    for refseq_id, sites in by_protein.items():
        positive_positions = {s["sibling_pos"] for s in sites}
        ks = proteome_k_sites.get(refseq_id, [])
        candidates = [k for k in ks if k not in positive_positions]
        if not candidates:
            continue
        for s in sites:
            neg_k = rng.choice(candidates)
            kept.append({
                "ProteinAccession": s["comp_accession"],
                "RefSeqAccession": refseq_id,
                "Position": s["sibling_pos"],
                "TrueLabel": 1,
                "Source": "feng2017",
            })
            negs.append({
                "ProteinAccession": s["comp_accession"],
                "RefSeqAccession": refseq_id,
                "Position": neg_k,
                "TrueLabel": 0,
                "Source": "synthetic_negative",
            })
    return kept, negs


def build_matches(
    positives: list[dict],
    negatives: list[dict],
    predictions_idx: dict[tuple[str, int], dict],
) -> list[dict]:
    """Join positives + negatives to predictions, compute TP/FP/TN/FN."""
    rows = []
    for row in positives + negatives:
        key = (row["RefSeqAccession"], int(row["Position"]))
        pred = predictions_idx.get(key)
        if pred is None:
            rows.append({
                **row,
                "MatchedSequence": "",
                "PositiveProbability": "",
                "PredictedLabel": "",
                "Status": "NS",
            })
            continue
        pred_label = pred["PredictedLabel"]
        true_label = row["TrueLabel"]
        if pred_label == 1 and true_label == 1:
            status = "TP"
        elif pred_label == 1 and true_label == 0:
            status = "FP"
        elif pred_label == 0 and true_label == 0:
            status = "TN"
        else:
            status = "FN"
        rows.append({
            **row,
            "MatchedSequence": pred["MatchedSequence"],
            "PositiveProbability": pred["PositiveProbability"],
            "PredictedLabel": pred_label,
            "Status": status,
        })
    return rows


def compute_metrics(matches: list[dict]) -> dict:
    """Compute precision, recall, F1, MCC, AUC-ROC, AUC-PR."""
    scored = [m for m in matches if m["Status"] != "NS"]
    y_true = np.array([m["TrueLabel"] for m in scored])
    y_pred = np.array([m["PredictedLabel"] for m in scored])
    y_prob = np.array([float(m["PositiveProbability"]) for m in scored])

    cm = Counter(m["Status"] for m in matches)
    out = {
        "n_total": len(matches),
        "n_scored": len(scored),
        "n_positives": int(y_true.sum()) if len(y_true) > 0 else 0,
        "n_negatives": int((1 - y_true).sum()) if len(y_true) > 0 else 0,
        "confusion_matrix": {
            "TP": cm.get("TP", 0),
            "FP": cm.get("FP", 0),
            "TN": cm.get("TN", 0),
            "FN": cm.get("FN", 0),
            "NS": cm.get("NS", 0),
        },
    }
    if len(scored) == 0 or len(set(y_true)) < 2:
        out["accuracy"] = float("nan")
        out["precision"] = float("nan")
        out["recall"] = float("nan")
        out["f1"] = float("nan")
        out["mcc"] = float("nan")
        out["auc_roc"] = float("nan")
        out["auc_pr"] = float("nan")
        return out

    out["accuracy"] = float((y_pred == y_true).mean())
    out["precision"] = float(precision_score(y_true, y_pred, zero_division=0))
    out["recall"] = float(recall_score(y_true, y_pred, zero_division=0))
    out["f1"] = float(f1_score(y_true, y_pred, zero_division=0))
    out["mcc"] = float(matthews_corrcoef(y_true, y_pred))
    out["auc_roc"] = float(roc_auc_score(y_true, y_prob))
    out["auc_pr"] = float(average_precision_score(y_true, y_prob))
    return out


def plot_pr_curve(matches: list[dict], output: Path) -> None:
    """Save PR curve plot."""
    scored = [m for m in matches if m["Status"] != "NS"]
    if not scored:
        return
    y_true = np.array([m["TrueLabel"] for m in scored])
    y_prob = np.array([float(m["PositiveProbability"]) for m in scored])
    p, r, _ = precision_recall_curve(y_true, y_prob)
    ap = average_precision_score(y_true, y_prob)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(r, p, label=f"AP = {ap:.3f}")
    ax.set_xlabel("Recall (sensitivity)")
    ax.set_ylabel("Precision")
    ax.set_title("RLSuccSite on D. officinale\n(1:1 same-protein synthetic negatives)")
    ax.set_xlim(0, 1.01)
    ax.set_ylim(0, 1.01)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


def run_full_evaluation(
    predictions_csv: str | Path,
    test_csv: str | Path,
    protein_fasta: str | Path,
    output_dir: str | Path,
    seed: int = 42,
) -> dict:
    """Run the full wet-lab evaluation pipeline.

    1. Load predictions (SequenceID, Sequence, PositiveProbability, PredictedLabel)
    2. Load wet-lab test sites (Feng et al 2017)
    3. Map test sites to RefSeq accessions via peptide matching
    4. Generate 1:1 same-protein synthetic negatives
    5. Join predictions to positives + negatives
    6. Compute precision, recall, F1, MCC, AUC-ROC, AUC-PR
    7. Write results to output_dir

    Returns:
        Dict of computed metrics.
    """
    predictions_csv = Path(predictions_csv)
    test_csv = Path(test_csv)
    protein_fasta = Path(protein_fasta)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/5] Loading predictions from {predictions_csv}")
    predictions_idx = load_predictions_index(predictions_csv)
    print(f"  {len(predictions_idx):,} predictions loaded")

    print(f"[2/5] Loading wet-lab test sites from {test_csv}")
    test_sites = load_test_sites(test_csv)
    print(f"  {len(test_sites)} wet-lab sites loaded")

    print("[3/5] Mapping test sites to RefSeq accessions (peptide matching)...")
    positives = map_test_to_refseq(test_sites, predictions_idx, load_proteome_k_sites(protein_fasta))
    print(f"  {len(positives)} positives mapped across "
          f"{len({p['refseq_accession'] for p in positives})} RefSeq proteins")

    print(f"[4/5] Generating 1:1 synthetic negatives (seed={seed})")
    proteome_k = load_proteome_k_sites(protein_fasta)
    rng = random.Random(seed)
    kept_pos, negs = build_negatives(positives, proteome_k, rng)
    n_dropped = len(positives) - len(kept_pos)
    print(f"  Kept positives : {len(kept_pos)}")
    print(f"  Negatives      : {len(negs)}")
    print(f"  Dropped        : {n_dropped}")

    print("[5/5] Joining + computing metrics")
    matches = build_matches(kept_pos, negs, predictions_idx)
    metrics = compute_metrics(matches)

    # Write outputs
    matches_path = output_dir / "matches.csv"
    with open(matches_path, "w", newline="") as f:
        if matches:
            fieldnames = [
                "ProteinAccession", "RefSeqAccession", "Position",
                "TrueLabel", "Source",
                "MatchedSequence", "PositiveProbability", "PredictedLabel", "Status",
            ]
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(matches)

    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))

    pr_path = output_dir / "pr_curve.png"
    plot_pr_curve(matches, pr_path)

    # Print report
    cm = metrics["confusion_matrix"]
    print()
    print("=" * 60)
    print("  Evaluation Results")
    print("=" * 60)
    print(f"  Total sites evaluated: {metrics['n_total']}")
    print(f"  Positives: {metrics['n_positives']}  |  Negatives: {metrics['n_negatives']}")
    print(f"  Confusion: TP={cm['TP']}  FP={cm['FP']}  TN={cm['TN']}  FN={cm['FN']}  NS={cm['NS']}")
    print()
    print(f"  Accuracy  : {metrics['accuracy']:.4f}")
    print(f"  Precision : {metrics['precision']:.4f}")
    print(f"  Recall    : {metrics['recall']:.4f}")
    print(f"  F1 Score  : {metrics['f1']:.4f}")
    print(f"  MCC       : {metrics['mcc']:.4f}")
    print(f"  AUC-ROC   : {metrics['auc_roc']:.4f}")
    print(f"  AUC-PR    : {metrics['auc_pr']:.4f}")
    print()
    print(f"  Results written to {output_dir}/")
    print("=" * 60)

    return metrics
