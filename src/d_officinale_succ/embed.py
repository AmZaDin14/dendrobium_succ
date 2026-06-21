"""Client wrapper for the Modal ProtT5 embedding app.

Provides a clean Python function that:
  1. Reads a fragments FASTA file
  2. Sends it to the Modal GPU app (modal/prott5_embed.py)
  3. Downloads the resulting .pt file from the Modal Volume
  4. Writes it to the local output path
"""

import subprocess
from pathlib import Path

from rich.console import Console

console = Console()

# Path to the Modal app (relative to project root)
MODAL_APP = "modal/prott5_embed.py"


def embed_fragments(
    fragments_fasta: str | Path,
    output_pt: str | Path,
    batch_size: int = 64,
) -> Path:
    """Embed 33-mer fragments with ProtT5-XL on Modal GPU.

    This runs `modal run modal/prott5_embed.py::embed` as a subprocess,
    then downloads the .pt result from the Modal Volume.

    Args:
        fragments_fasta: Path to the fragments FASTA (from extract step).
        output_pt: Where to write the .pt file locally.
        batch_size: GPU batch size (default 64).

    Returns:
        Path to the written .pt file.
    """
    fragments_fasta = Path(fragments_fasta)
    output_pt = Path(output_pt)
    output_name = output_pt.name

    if not fragments_fasta.exists():
        raise FileNotFoundError(f"Fragments FASTA not found: {fragments_fasta}")

    console.print(f"[cyan]Embedding fragments with ProtT5 on Modal GPU...[/cyan]")
    console.print(f"  Input:  {fragments_fasta}")
    console.print(f"  Output: {output_pt}")

    # Step 1: Run embedding on Modal
    cmd = [
        "modal", "run", f"{MODAL_APP}::embed",
        "--fasta-path", str(fragments_fasta),
        "--output-name", output_name,
        "--batch-size", str(batch_size),
    ]
    console.print(f"  [dim]$ {' '.join(cmd)}[/dim]")
    subprocess.run(cmd, check=True)

    # Step 2: Download .pt from Modal Volume
    output_pt.parent.mkdir(parents=True, exist_ok=True)
    download_cmd = [
        "modal", "volume", "get", "prott5-output",
        output_name, str(output_pt),
    ]
    console.print(f"  [dim]$ {' '.join(download_cmd)}[/dim]")
    subprocess.run(download_cmd, check=True)

    if not output_pt.exists():
        raise RuntimeError(
            f"Expected output .pt not found after download: {output_pt}"
        )

    size_mb = output_pt.stat().st_size / (1024 * 1024)
    console.print(f"[green]✓ Downloaded[/green] {output_pt} ({size_mb:.1f} MB)")
    return output_pt


def download_model():
    """One-time: download ProtT5-XL weights to the Modal Volume.

    Run this once before the first embedding job.
    """
    console.print("[cyan]Downloading ProtT5-XL to Modal Volume...[/cyan]")
    cmd = ["modal", "run", f"{MODAL_APP}::download_model"]
    subprocess.run(cmd, check=True)
    console.print("[green]✓ Model cached on Volume 'prott5-model'[/green]")
