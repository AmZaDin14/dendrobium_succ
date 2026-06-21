"""Wrapper to run RLSuccSite's Models/Predict.py as a subprocess.

RLSuccSite's Predict.py is a self-contained CPU inference script with its
own virtual environment (torch, torchrl, tensordict, protlearn, etc.).
Rather than reimplementing the ensemble logic, we call it directly via
RLSuccSite's .venv Python.

Predict.py CLI:
    --prott5_features_pt  .pt dict with 'ids' + 'features' [N,1024]
    --fragments_fasta     33-mer FASTA centered on K
    --output              CSV output path
    --num_workers         parallel workers for feature extraction (default 6)
    --batch_size          streaming batch size (default 2048)

Output CSV columns: SequenceID, Sequence, PositiveProbability, PredictedLabel
"""

import subprocess
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)

# RLSuccSite is a sibling directory: ../RLSuccSite
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
RLSUCCSITE_DIR = _PROJECT_ROOT.parent / "RLSuccSite"
RLSUCCSITE_PYTHON = RLSUCCSITE_DIR / ".venv" / "bin" / "python"
PREDICT_PY = RLSUCCSITE_DIR / "Models" / "Predict.py"


def run_predict(
    prott5_pt: str | Path,
    fragments_fasta: str | Path,
    output_csv: str | Path,
    rlsuccsite_dir: str | Path | None = None,
    num_workers: int = 6,
    batch_size: int = 2048,
) -> Path:
    """Run RLSuccSite ensemble prediction (ProtT5 + TPEMPPS_CCP).

    Args:
        prott5_pt: Path to the ProtT5 features .pt file.
        fragments_fasta: Path to the 33-mer fragments FASTA.
        output_csv: Path to write the predictions CSV.
        rlsuccsite_dir: Override RLSuccSite directory (auto-detected if None).
        num_workers: Parallel workers for hand-crafted feature extraction.
        batch_size: Streaming batch size.

    Returns:
        Path to the output CSV.
    """
    prott5_pt = Path(prott5_pt)
    fragments_fasta = Path(fragments_fasta)
    output_csv = Path(output_csv)

    # Resolve RLSuccSite paths
    base = Path(rlsuccsite_dir) if rlsuccsite_dir else RLSUCCSITE_DIR
    python = base / ".venv" / "bin" / "python"
    predict_py = base / "Models" / "Predict.py"

    if not python.exists():
        raise FileNotFoundError(
            f"RLSuccSite Python not found: {python}\n"
            f"Set --rlsuccsite-dir or ensure RLSuccSite is at {RLSUCCSITE_DIR}"
        )
    if not predict_py.exists():
        raise FileNotFoundError(f"Predict.py not found: {predict_py}")

    for label, p in [("ProtT5 features", prott5_pt), ("Fragments FASTA", fragments_fasta)]:
        if not p.exists():
            raise FileNotFoundError(f"{label} not found: {p}")

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(python), str(predict_py),
        "--prott5_features_pt", str(prott5_pt),
        "--fragments_fasta", str(fragments_fasta),
        "--output", str(output_csv),
        "--num_workers", str(num_workers),
        "--batch_size", str(batch_size),
    ]

    logger.info("Running RLSuccSite ensemble prediction...")
    logger.info(f"  ProtT5:   {prott5_pt}")
    logger.info(f"  Fragments: {fragments_fasta}")
    logger.info(f"  Output:   {output_csv}")
    logger.debug(f"$ {' '.join(cmd)}")

    # Run from RLSuccSite dir so its relative imports (Feature.*, Models.*) work
    subprocess.run(cmd, check=True, cwd=str(base))

    if not output_csv.exists():
        raise RuntimeError(f"Expected output CSV not found: {output_csv}")

    # Report summary
    import csv
    with open(output_csv) as f:
        reader = csv.DictReader(f)
        total = 0
        positives = 0
        for row in reader:
            total += 1
            if row["PredictedLabel"] == "1":
                positives += 1

    logger.info(
        f"Predictions saved → {output_csv} ({total} sites, {positives} positive)",
        extra={"output_path": output_csv, "count": total, "positives": positives},
    )
    return output_csv
