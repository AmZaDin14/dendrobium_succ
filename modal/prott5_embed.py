"""Modal app: GPU-accelerated ProtT5-XL embedding for protein fragments.

This replaces RLSuccSite's Feature/ProtT5_combined.py (CPU, slow) with a
Modal-hosted GPU pipeline that:

  1. Downloads Rostlab/prot_t5_xl_uniref50 once → cached on a Modal Volume
  2. Loads the model into a GPU container (L4, 24 GB)
  3. Tokenizes 33-mer fragments, runs the T5 encoder, extracts the center
     residue embedding (index 16 → 1024-D vector)
  4. Saves a .pt file with {'ids': list[str], 'features': Tensor[N, 1024]}

Usage (from project root):

    # One-time: download ProtT5 weights to Modal Volume
    modal run modal/prott5_embed.py::download_model

    # Embed a fragments FASTA
    modal run modal/prott5_embed.py::embed --fasta-path data/processed/fragments.fasta --output-name features.pt

    # Download the result from the Modal Volume
    modal volume get prott5-output features.pt data/processed/features.pt

The output .pt format matches what RLSuccSite's Models/Predict.py expects:
    torch.load(path) → {'ids': list[str], 'features': Tensor[N, 1024]}
"""

import re
import time

import modal

app = modal.App("d-officinale-prott5-embed")

# ── Volumes ──────────────────────────────────────────────────────────
HF_HOME = "/root/.cache/huggingface"
OUTPUT_DIR = "/output"

MODEL_VOLUME = modal.Volume.from_name("prott5-model", create_if_missing=True)
OUTPUT_VOLUME = modal.Volume.from_name("prott5-output", create_if_missing=True)

# ── Image ────────────────────────────────────────────────────────────
# Heavy pip installs first (better Docker cache layering), then app code.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .uv_pip_install(
        "torch==2.7.1",
        index_url="https://download.pytorch.org/whl/cu128",
    )
    .uv_pip_install(
        "transformers==4.40",
        "sentencepiece>=0.2.1",
        "numpy<2",
        "tqdm",
    )
    .env({"HF_HOME": HF_HOME})
)

# ── Model download (run once) ────────────────────────────────────────


@app.function(
    image=image,
    volumes={HF_HOME: MODEL_VOLUME},
    timeout=600,
)
def download_model():
    """Download Rostlab/prot_t5_xl_uniref50 to the Modal Volume for reuse."""
    from transformers import T5EncoderModel, T5Tokenizer

    print("Downloading ProtT5-XL tokenizer + model to Volume...")
    tokenizer = T5Tokenizer.from_pretrained(
        "Rostlab/prot_t5_xl_uniref50", do_lower_case=False
    )
    model = T5EncoderModel.from_pretrained("Rostlab/prot_t5_xl_uniref50")
    MODEL_VOLUME.commit()
    print("Done. Model cached on Volume 'prott5-model'.")


# ── Embedding class (GPU container) ──────────────────────────────────


@app.cls(
    image=image,
    gpu="L40S",
    volumes={HF_HOME: MODEL_VOLUME, OUTPUT_DIR: OUTPUT_VOLUME},
    cpu=8.0,
    memory=32768,
    timeout=1800,
    startup_timeout=600,
)
class ProtT5Embedder:
    """GPU ProtT5 embedder that persists across calls in the same container."""

    @modal.enter()
    def setup(self):
        import torch
        from transformers import T5EncoderModel, T5Tokenizer

        # Optimize GPU performance
        torch.set_float32_matmul_precision("high")

        self.torch = torch
        print("Loading ProtT5-XL from Volume...")
        self.tokenizer = T5Tokenizer.from_pretrained(
            "Rostlab/prot_t5_xl_uniref50",
            do_lower_case=False,
            local_files_only=True,
        )
        self.model = T5EncoderModel.from_pretrained(
            "Rostlab/prot_t5_xl_uniref50",
            local_files_only=True,
        )
        self.model.eval()
        self.device = torch.device("cuda")
        self.model = self.model.to(self.device)
        print("ProtT5-XL loaded on GPU (L40S, precision=high).")

    @modal.method()
    def embed_fasta(
        self,
        fasta_content: str,
        output_filename: str,
        batch_size: int = 512,
    ) -> str:
        """Embed 33-mer fragments and save .pt to the output Volume.

        Args:
            fasta_content: Full text of a fragments FASTA file. Each entry
                is two lines: header (>id|pos_N) and 33-char sequence.
            output_filename: Filename for the .pt output (written to Volume).
            batch_size: Sequences per GPU forward pass.

        Returns:
            The output_filename (for later `modal volume get` retrieval).
        """
        torch = self.torch

        # ── Parse FASTA ──────────────────────────────────────────────
        ids, seqs = [], []
        lines = fasta_content.strip().split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith(">"):
                ids.append(line)
                seqs.append(lines[i + 1].strip())
                i += 2
            else:
                i += 1

        print(f"Embedding {len(seqs)} fragments (batch_size={batch_size})...")

        # ── Batched GPU inference ────────────────────────────────────
        all_features = []
        for start in range(0, len(seqs), batch_size):
            batch = seqs[start : start + batch_size]

            # Clean non-standard AAs (match RLSuccSite: U/Z/O/B → X)
            batch = [re.sub(r"[UZOB]", "X", s) for s in batch]
            # ProtT5 expects space-separated residues
            batch = [" ".join(s) for s in batch]

            encoded = self.tokenizer(
                batch,
                add_special_tokens=True,
                padding=True,
                return_tensors="pt",
            ).to(self.device)

            with torch.no_grad():
                embeddings = self.model(**encoded)[0]  # [B, L, 1024]

            for j in range(len(batch)):
                seq_len = (encoded["attention_mask"][j] == 1).sum().item()
                seq_emb = embeddings[j][: seq_len - 1]  # drop </s>
                center = seq_emb[16]  # center residue of 33-mer (0-based)
                all_features.append(center.cpu())

            if (start // batch_size + 1) % 10 == 0:
                print(f"  ...{min(start + batch_size, len(seqs))}/{len(seqs)}")

        features = torch.stack(all_features)  # [N, 1024]
        print(f"Features shape: {features.shape}")

        # ── Save to Volume ───────────────────────────────────────────
        output_path = f"{OUTPUT_DIR}/{output_filename}"
        torch.save({"ids": ids, "features": features}, output_path)
        OUTPUT_VOLUME.commit()
        print(f"Saved → Volume 'prott5-output' / {output_filename}")

        return output_filename


# ── CLI entrypoint ───────────────────────────────────────────────────


@app.local_entrypoint()
def embed(
    fasta_path: str,
    output_name: str = "features.pt",
    batch_size: int = 512,
):
    """Embed a fragments FASTA file with ProtT5 on GPU.

    Usage:
        modal run modal/prott5_embed.py::embed \
            --fasta-path data/processed/fragments.fasta \
            --output-name features.pt

    Then download the result:
        modal volume get prott5-output features.pt data/processed/features.pt
    """
    from pathlib import Path

    fasta_content = Path(fasta_path).read_text()
    filename = ProtT5Embedder().embed_fasta.remote(
        fasta_content, output_name, batch_size
    )
    print(f"\n✓ Embedding complete. Download with:")
    print(f"  modal volume get prott5-output {filename} data/processed/{filename}")
