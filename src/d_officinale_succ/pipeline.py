"""Full pipeline orchestration: extract → embed → predict.

Given a protein FASTA, runs all three steps end-to-end:
  1. Extract 33-mer fragments around each K (CPU, local)
  2. Embed fragments with ProtT5-XL (GPU, Modal)
  3. Run RLSuccSite ensemble prediction (CPU, local via RLSuccSite's venv)
"""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from .embed import download_model, embed_fragments
from .extract import extract_fragments
from .predict import run_predict

console = Console()


def run_pipeline(
    input_fasta: str | Path,
    output_csv: str | Path,
    work_dir: str | Path | None = None,
    skip_model_download: bool = False,
    batch_size: int = 64,
    num_workers: int = 6,
) -> Path:
    """Run the full succinylation prediction pipeline.

    Args:
        input_fasta: Path to the input protein FASTA (.faa / .fasta).
        output_csv: Path to the final predictions CSV.
        work_dir: Directory for intermediate files (default: alongside input).
        skip_model_download: Skip the one-time ProtT5 download step.
        batch_size: GPU batch size for ProtT5 embedding.
        num_workers: CPU workers for hand-crafted feature extraction.

    Returns:
        Path to the output CSV.
    """
    input_fasta = Path(input_fasta)
    output_csv = Path(output_csv)

    if work_dir is None:
        work_dir = output_csv.parent / "intermediate"
    else:
        work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    fragments_fasta = work_dir / "fragments.fasta"
    features_pt = work_dir / "features.pt"

    # ── Step 0: One-time model download ─────────────────────────────
    if not skip_model_download:
        console.rule("[bold cyan]Step 0: Download ProtT5-XL to Modal Volume[/bold cyan]")
        download_model()

    # ── Step 1: Extract fragments ───────────────────────────────────
    console.rule("[bold cyan]Step 1: Extract 33-mer fragments around each K[/bold cyan]")
    n_fragments = extract_fragments(input_fasta, fragments_fasta)

    if n_fragments == 0:
        console.print("[yellow]No lysine (K) sites found. Nothing to predict.[/yellow]")
        return output_csv

    # ── Step 2: ProtT5 embedding (Modal GPU) ────────────────────────
    console.rule("[bold cyan]Step 2: ProtT5-XL embedding (Modal GPU)[/bold cyan]")
    embed_fragments(fragments_fasta, features_pt, batch_size=batch_size)

    # ── Step 3: RLSuccSite ensemble prediction ──────────────────────
    console.rule("[bold cyan]Step 3: RLSuccSite ensemble prediction[/bold cyan]")
    run_predict(
        prott5_pt=features_pt,
        fragments_fasta=fragments_fasta,
        output_csv=output_csv,
        num_workers=num_workers,
    )

    # ── Summary ─────────────────────────────────────────────────────
    console.rule("[bold green]Pipeline complete[/bold green]")

    table = Table(title="Pipeline Summary")
    table.add_column("Step", style="cyan")
    table.add_column("Output", style="white")
    table.add_column("Size", style="dim")
    table.add_row("Input proteins", str(input_fasta), f"{input_fasta.stat().st_size / 1024:.0f} KB")
    table.add_row("Fragments", str(fragments_fasta), f"{n_fragments} sites")
    table.add_row("ProtT5 features", str(features_pt), f"{features_pt.stat().st_size / (1024*1024):.1f} MB")
    table.add_row("Predictions", str(output_csv), f"{output_csv.stat().st_size / 1024:.0f} KB")
    console.print(table)

    return output_csv
