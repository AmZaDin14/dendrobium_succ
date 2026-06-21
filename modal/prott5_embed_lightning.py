"""Modal app: PyTorch Lightning-based ProtT5 embedding for protein fragments.

This implementation uses PyTorch Lightning with DataLoader for optimized
batch processing, similar to the original notebook approach.

Key differences from prott5_embed.py:
- Uses PyTorch Lightning for better GPU utilization
- DataLoader with multiprocessing for data loading
- Optimized batch processing with pin_memory
- Same output format as the original notebook
"""

import os
import re
import modal

app = modal.App("d-officinale-prott5-embed-lightning")

# ── Volumes ──────────────────────────────────────────────────────────
HF_HOME = "/root/.cache/huggingface"
OUTPUT_DIR = "/output"

MODEL_VOLUME = modal.Volume.from_name("prott5-model", create_if_missing=True)
OUTPUT_VOLUME = modal.Volume.from_name("prott5-output", create_if_missing=True)

# ── Image ────────────────────────────────────────────────────────────
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
        "lightning==2.5.0",
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


# ── Embedding function ───────────────────────────────────────────────

@app.cls(
    image=image,
    gpu="L40S",
    volumes={HF_HOME: MODEL_VOLUME, OUTPUT_DIR: OUTPUT_VOLUME},
    cpu=8.0,
    memory=32768,
    timeout=1800,
    startup_timeout=600,
)
class ProtT5EmbedderLightning:
    """GPU ProtT5 embedder using PyTorch Lightning."""

    @modal.enter()
    def setup(self):
        import torch
        # Optimize GPU performance
        torch.set_float32_matmul_precision("high")
        print("ProtT5-XL Lightning embedder initialized (L40S, precision=high).")

    @modal.method()
    def embed_fasta(
        self,
        fasta_content: str,
        output_filename: str,
        batch_size: int = 512,
        num_workers: int = 4,
    ) -> str:
        """Embed 33-mer fragments using PyTorch Lightning.

        Args:
            fasta_content: Content of the fragments FASTA file.
            output_filename: Filename for the .pt output (written to Volume).
            batch_size: Sequences per GPU forward pass.
            num_workers: DataLoader workers for data loading.

        Returns:
            The output_filename (for later `modal volume get` retrieval).
        """
        import torch
        import pytorch_lightning as pl
        from torch.utils.data import Dataset, DataLoader
        from transformers import T5EncoderModel, T5Tokenizer
        import tempfile
        
        # Define Dataset class
        class FastaDataset(Dataset):
            def __init__(self, file_path):
                with open(file_path, 'r') as f:
                    lines = [l.strip() for l in f if l.strip()]
                self.titles = lines[0::2]
                raw_seqs = lines[1::2]
                self.seqs = [" ".join(re.sub(r"[UZOB]", "X", s)) for s in raw_seqs]

            def __len__(self):
                return len(self.titles)

            def __getitem__(self, idx):
                return idx, self.titles[idx], self.seqs[idx]
        
        # Define Lightning Module
        class ProtT5Extractor(pl.LightningModule):
            def __init__(self, model_id, center_idx=16):
                super().__init__()
                self.save_hyperparameters()
                self.tokenizer = T5Tokenizer.from_pretrained(model_id, do_lower_case=False, local_files_only=True)
                self.model = T5EncoderModel.from_pretrained(model_id, local_files_only=True)
                self.center_idx = center_idx

            def forward(self, input_ids, attention_mask):
                return self.model(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state

            def on_predict_start(self):
                self.ids_buffer = []
                self.feat_buffer = []

            @torch.no_grad()
            def predict_step(self, batch, batch_idx, dataloader_idx=0):
                indices, titles, seqs = batch

                inputs = self.tokenizer(
                    list(seqs),
                    add_special_tokens=True,
                    padding=True,
                    return_tensors='pt'
                ).to(self.device)

                embeddings = self(inputs['input_ids'], inputs['attention_mask'])

                for j in range(len(seqs)):
                    valid_len = int(inputs['attention_mask'][j].sum().item())
                    seq_emb = embeddings[j][:valid_len]

                    if seq_emb.shape[0] > 0:
                        seq_emb = seq_emb[:-1]

                    if seq_emb.shape[0] <= self.center_idx:
                        continue

                    vec = seq_emb[self.center_idx]

                    self.ids_buffer.append((int(indices[j]), str(titles[j])))
                    self.feat_buffer.append(vec.detach().cpu())

                return None

            def on_predict_end(self):
                if len(self.feat_buffer) == 0:
                    raise RuntimeError("No features were extracted.")

                feats = torch.stack(self.feat_buffer, dim=0)
                idxs = torch.tensor([i for i, _ in self.ids_buffer], dtype=torch.long)
                titles = [t for _, t in self.ids_buffer]

                out = {
                    'indices': idxs,
                    'ids': titles,
                    'features': feats
                }

                output_path = os.environ.get('OUTPUT_PATH', '/output/features.pt')
                torch.save(out, output_path)
                print(f"Saved features to {output_path} | shape={feats.shape}")
        
        # Define DataModule
        class SimpleDataModule(pl.LightningDataModule):
            def __init__(self, fasta_path, batch_size=512, num_workers=4):
                super().__init__()
                self.fasta_path = fasta_path
                self.batch_size = batch_size
                self.num_workers = num_workers

            def setup(self, stage=None):
                self.ds = FastaDataset(self.fasta_path)

            def predict_dataloader(self):
                return DataLoader(
                    self.ds,
                    batch_size=self.batch_size,
                    shuffle=False,
                    num_workers=self.num_workers,
                    pin_memory=True
                )
        
        output_path = f"{OUTPUT_DIR}/{output_filename}"
        os.environ['OUTPUT_PATH'] = output_path

        # Write fasta_content to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
            f.write(fasta_content)
            temp_fasta_path = f.name

        print(f"Embedding with Lightning (batch_size={batch_size}, workers={num_workers})...")

        # Create data module and model
        dm = SimpleDataModule(temp_fasta_path, batch_size=batch_size, num_workers=num_workers)
        model = ProtT5Extractor("Rostlab/prot_t5_xl_uniref50")

        # Create trainer
        trainer = pl.Trainer(
            accelerator="gpu",
            devices=1,
            logger=False,
            enable_checkpointing=False,
            enable_progress_bar=False,
        )

        # Run prediction
        trainer.predict(model, datamodule=dm)

        # Clean up temp file
        os.unlink(temp_fasta_path)

        OUTPUT_VOLUME.commit()
        print(f"Saved → Volume 'prott5-output' / {output_filename}")

        return output_filename


# ── CLI entrypoint ───────────────────────────────────────────────────

@app.local_entrypoint()
def embed(
    fasta_path: str,
    output_name: str = "features.pt",
    batch_size: int = 512,
    num_workers: int = 4,
):
    """Embed a fragments FASTA file with ProtT5 using PyTorch Lightning.

    Usage:
        modal run modal/prott5_embed_lightning.py::embed \
            --fasta-path data/processed/fragments.fasta \
            --output-name features.pt

    Then download the result:
        modal volume get prott5-output features.pt data/processed/features.pt
    """
    from pathlib import Path

    # Read file content
    fasta_content = Path(fasta_path).read_text()

    filename = ProtT5EmbedderLightning().embed_fasta.remote(
        fasta_content, output_name, batch_size, num_workers
    )
    print(f"\n✓ Embedding complete. Download with:")
    print(f"  modal volume get prott5-output {filename} data/processed/{filename}")
