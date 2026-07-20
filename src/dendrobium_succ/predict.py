"""Wrapper to run RLSuccSite's Models/Predict.py as a subprocess.

RLSuccSite's Predict.py is a self-contained CPU inference script that
uses torch, torchrl, tensordict, and protlearn. All these deps are
installed in the same `.venv` as the harness via `uv sync` (see
pyproject.toml). We call Predict.py as a subprocess using the current
Python interpreter so its relative imports (Feature.*, Models.*) work
correctly.

Predict.py CLI:
    --prott5_features_pt  .pt dict with 'ids' + 'features' [N,1024]
    --fragments_fasta     33-mer FASTA centered on K
    --output              CSV output path
    --num_workers         parallel workers for feature extraction (default 6)
    --batch_size          streaming batch size (default 2048)

Output CSV columns: SequenceID, Sequence, PositiveProbability, PredictedLabel
"""

import subprocess
import sys
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)

# Local models directory (self-contained, ships with the repo)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_MODELS_DIR = _PROJECT_ROOT / "models" / "rlsuccsite"


def run_predict(
    prott5_pt: str | Path,
    fragments_fasta: str | Path,
    output_csv: str | Path,
    rlsuccsite_dir: str | Path | None = None,
    num_workers: int = 6,
    batch_size: int = 2048,
) -> Path:
    """Run RLSuccSite ensemble prediction (ProtT5 + TPEMPPS_CCP).

    Uses the current Python interpreter (sys.executable), which has all
    predict deps installed via ``uv sync``.

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
    prott5_pt = Path(prott5_pt).resolve()
    fragments_fasta = Path(fragments_fasta).resolve()
    output_csv = Path(output_csv).resolve()

    # Determine which RLSuccSite directory to use
    if rlsuccsite_dir:
        base = Path(rlsuccsite_dir)
    elif LOCAL_MODELS_DIR.exists() and (LOCAL_MODELS_DIR / "Models" / "Predict.py").exists():
        base = LOCAL_MODELS_DIR
        logger.info(f"Using local RLSuccSite models: {base}")
    else:
        raise FileNotFoundError(
            f"RLSuccSite not found at {LOCAL_MODELS_DIR}.\n"
            f"Re-clone the repo or pass --rlsuccsite-dir."
        )

    predict_py = base / "Models" / "Predict.py"
    if not predict_py.exists():
        raise FileNotFoundError(f"Predict.py not found: {predict_py}")

    for label, p in [("ProtT5 features", prott5_pt), ("Fragments FASTA", fragments_fasta)]:
        if not p.exists():
            raise FileNotFoundError(f"{label} not found: {p}")

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    # Use the current Python interpreter — all predict deps are available
    python = sys.executable

    cmd = [
        str(python), str(predict_py),
        "--prott5_features_pt", str(prott5_pt),
        "--fragments_fasta", str(fragments_fasta),
        "--output", str(output_csv),
        "--num_workers", str(num_workers),
        "--batch_size", str(batch_size),
    ]

    logger.info("Running RLSuccSite ensemble prediction...")
    logger.info(f"  Interpreter: {python}")
    logger.info(f"  ProtT5:      {prott5_pt}")
    logger.info(f"  Fragments:   {fragments_fasta}")
    logger.info(f"  Output:      {output_csv}")
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
