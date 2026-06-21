"""CLI for d_officinale_succ — reproducible succinylation site prediction.

Usage:
    d-officinale-succ extract --input-fasta proteins.faa --output-fasta fragments.fasta
    d-officinale-succ download-model
    d-officinale-succ embed --fragments-fasta fragments.fasta --output-pt features.pt
    d-officinale-succ predict --prott5-pt features.pt --fragments-fasta fragments.fasta --output-csv preds.csv
    d-officinale-succ run --input-fasta proteins.faa --output-csv preds.csv
"""

from pathlib import Path

import typer
from rich.console import Console

from .embed import download_model, embed_fragments
from .extract import extract_fragments
from .pipeline import run_pipeline
from .predict import run_predict

console = Console()
app = typer.Typer(
    name="d-officinale-succ",
    help="Reproducible succinylation site prediction for Daucus officinale using RLSuccSite.",
    no_args_is_help=True,
)


@app.command()
def extract(
    input_fasta: Path = typer.Option(..., "--input-fasta", "-i", help="Input protein FASTA (.faa/.fasta)"),
    output_fasta: Path = typer.Option(..., "--output-fasta", "-o", help="Output fragments FASTA path"),
    window_size: int = typer.Option(33, "--window-size", "-w", help="Fragment window size (odd)"),
):
    """Extract 33-mer fragments centered on each lysine (K) residue."""
    count = extract_fragments(input_fasta, output_fasta, window_size)
    console.print(f"\n[bold green]Done.[/bold green] {count} fragments → {output_fasta}")


@app.command(name="download-model")
def download_model_cmd():
    """One-time: download ProtT5-XL weights to Modal Volume."""
    download_model()


@app.command()
def embed(
    fragments_fasta: Path = typer.Option(..., "--fragments-fasta", "-f", help="Fragments FASTA from extract step"),
    output_pt: Path = typer.Option(..., "--output-pt", "-o", help="Output .pt file path"),
    batch_size: int = typer.Option(64, "--batch-size", "-b", help="GPU batch size"),
):
    """Embed fragments with ProtT5-XL on Modal GPU."""
    embed_fragments(fragments_fasta, output_pt, batch_size)


@app.command()
def predict(
    prott5_pt: Path = typer.Option(..., "--prott5-pt", help="ProtT5 features .pt file"),
    fragments_fasta: Path = typer.Option(..., "--fragments-fasta", "-f", help="Fragments FASTA"),
    output_csv: Path = typer.Option(..., "--output-csv", "-o", help="Output predictions CSV"),
    rlsuccsite_dir: Path | None = typer.Option(None, "--rlsuccsite-dir", help="Override RLSuccSite directory"),
    num_workers: int = typer.Option(6, "--num-workers", "-n", help="Parallel workers for feature extraction"),
    batch_size: int = typer.Option(2048, "--batch-size", "-b", help="Streaming batch size"),
):
    """Run RLSuccSite ensemble prediction (ProtT5 + TPEMPPS_CCP)."""
    run_predict(
        prott5_pt=prott5_pt,
        fragments_fasta=fragments_fasta,
        output_csv=output_csv,
        rlsuccsite_dir=rlsuccsite_dir,
        num_workers=num_workers,
        batch_size=batch_size,
    )


@app.command()
def run(
    input_fasta: Path = typer.Option(..., "--input-fasta", "-i", help="Input protein FASTA"),
    output_csv: Path = typer.Option(..., "--output-csv", "-o", help="Output predictions CSV"),
    work_dir: Path | None = typer.Option(None, "--work-dir", help="Directory for intermediate files"),
    skip_model_download: bool = typer.Option(False, "--skip-model-download", help="Skip ProtT5 download (already done)"),
    batch_size: int = typer.Option(64, "--batch-size", "-b", help="GPU batch size"),
    num_workers: int = typer.Option(6, "--num-workers", "-n", help="CPU workers for feature extraction"),
):
    """Full pipeline: extract → embed → predict."""
    run_pipeline(
        input_fasta=input_fasta,
        output_csv=output_csv,
        work_dir=work_dir,
        skip_model_download=skip_model_download,
        batch_size=batch_size,
        num_workers=num_workers,
    )


if __name__ == "__main__":
    app()
