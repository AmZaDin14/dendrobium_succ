"""Full pipeline orchestration: fetch → extract → embed → predict.

Given a protein FASTA (or an NCBI accession to fetch one), runs all steps:
  0. (Optional) Fetch protein FASTA from NCBI Datasets API
  1. Extract 33-mer fragments around each K (CPU, local)
  2. Embed fragments with ProtT5-XL (GPU, Modal)
  3. Run RLSuccSite ensemble prediction (CPU, local via RLSuccSite's venv)
"""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from .embed import download_model, embed_fragments
from .extract import extract_fragments
from .fetch import fetch as fetch_fasta
from .logging_config import get_logger
from .predict import run_predict

logger = get_logger(__name__)
console = Console()  # Keep for rich table rendering


def run_pipeline(
    output_csv: str | Path,
    input_fasta: str | Path | None = None,
    accession: str | None = None,
    organism: str | None = None,
    work_dir: str | Path | None = None,
    skip_model_download: bool = False,
    batch_size: int = 512,
    num_workers: int = 6,
) -> Path:
    """Run the full succinylation prediction pipeline.

    Provide exactly one of *input_fasta*, *accession*, or *organism*.
    If accession/organism is given, the protein FASTA is fetched from NCBI first.

    Args:
        output_csv: Path to the final predictions CSV.
        input_fasta: Path to an existing protein FASTA (skip fetch).
        accession: NCBI assembly accession to fetch (e.g. "GCF_001605985.2").
        organism: Organism name to search NCBI (e.g. "Daucus carota").
        work_dir: Directory for intermediate files (default: alongside output).
        skip_model_download: Skip the one-time ProtT5 download step.
        batch_size: GPU batch size for ProtT5 embedding.
        num_workers: CPU workers for hand-crafted feature extraction.

    Returns:
        Path to the output CSV.
    """
    output_csv = Path(output_csv)

    if work_dir is None:
        work_dir = output_csv.parent / "intermediate"
    else:
        work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    fragments_fasta = work_dir / "fragments.fasta"
    features_pt = work_dir / "features.pt"

    # ── Step 0a: One-time model download ────────────────────────────
    if not skip_model_download:
        logger.info("Step 0: Download ProtT5-XL to Modal Volume")
        download_model()

    # ── Step 0b: Fetch protein FASTA from NCBI (if needed) ──────────
    if input_fasta is None:
        logger.info("Step 1: Fetch protein FASTA from NCBI")
        input_fasta = work_dir / "proteins.faa"
        fetch_fasta(
            organism=organism,
            accession=accession,
            output_fasta=input_fasta,
        )
    else:
        input_fasta = Path(input_fasta)

    # ── Step 2: Extract fragments ───────────────────────────────────
    logger.info("Step 2: Extract 33-mer fragments around each K")
    n_fragments = extract_fragments(input_fasta, fragments_fasta)

    if n_fragments == 0:
        logger.warning("No lysine (K) sites found. Nothing to predict.")
        return output_csv

    # ── Step 3: ProtT5 embedding (Modal GPU) ────────────────────────
    logger.info("Step 3: ProtT5-XL embedding (Modal GPU)")
    embed_fragments(fragments_fasta, features_pt, batch_size=batch_size)

    # ── Step 4: RLSuccSite ensemble prediction ──────────────────────
    logger.info("Step 4: RLSuccSite ensemble prediction")
    run_predict(
        prott5_pt=features_pt,
        fragments_fasta=fragments_fasta,
        output_csv=output_csv,
        num_workers=num_workers,
    )

    # ── Summary ─────────────────────────────────────────────────────
    logger.info("Pipeline complete")

    table = Table(title="Pipeline Summary")
    table.add_column("Step", style="cyan")
    table.add_column("Output", style="white")
    table.add_column("Size", style="dim")
    table.add_row("Input proteins", str(input_fasta), f"{input_fasta.stat().st_size / 1024:.0f} KB")
    table.add_row("Fragments", str(fragments_fasta), f"{n_fragments} sites")
    table.add_row("ProtT5 features", str(features_pt), f"{features_pt.stat().st_size / (1024*1024):.1f} MB")
    table.add_row("Predictions", str(output_csv), f"{output_csv.stat().st_size / 1024:.0f} KB")
    
    # Render table to string for logging
    from io import StringIO
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=False)
    console.print(table)
    logger.info(string_io.getvalue())

    return output_csv
