"""Fetch protein FASTA from NCBI Datasets v2 API.

Two modes:
  1. By assembly accession (primary, reliable):
     download_protein_fasta("GCF_001605985.2", "data/input/proteins.faa")

  2. By organism name (searches NCBI Taxonomy, picks first RefSeq assembly):
     search_assemblies("Daucus carota") → ["GCF_001625215.2", ...]

API reference: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/rest-api/
  - Search:  GET /genome/taxon/{name}/dataset_report?returned_content=ASSM_ACC
  - Download: GET /genome/accession/{acc}/download?include_annotation_type=PROT_FASTA
    → returns ZIP; extract ncbi_dataset/data/{acc}/protein.faa

Auth: optional. Set NCBI_API_KEY env var for 10 req/s (default 5 req/s).

Note: "Daucus catenatum" is NOT a valid NCBI Taxonomy name. Use the
assembly accession GCF_001605985.2 directly, or search "Daucus carota".
"""

import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.ncbi.nlm.nih.gov/datasets/v2"


def _get_api_key() -> str | None:
    return os.environ.get("NCBI_API_KEY")


def _build_url(path: str, params: dict | None = None) -> str:
    """Build a full API URL with optional query params + API key."""
    url = f"{BASE_URL}{path}"
    key = _get_api_key()
    if params:
        p = dict(params)
        if key:
            p["api_key"] = key
        url += "?" + urllib.parse.urlencode(p)
    elif key:
        url += "?api_key=" + urllib.parse.quote(key)
    return url


def search_assemblies(
    organism: str,
    refseq_only: bool = True,
    page_size: int = 1000,
) -> list[dict]:
    """Search NCBI for genome assemblies by organism name or taxon ID.

    Args:
        organism: Scientific name (e.g. "Daucus carota") or NCBI taxon ID
            (e.g. "4039"). Must match a valid NCBI Taxonomy node.
        refseq_only: If True, filter to RefSeq assemblies only.
        page_size: Results per page (max 1000).

    Returns:
        List of dicts, each with keys:
            accession       — the version requested
            current_accession — latest version (use this for download)
            organism_name   — e.g. "Daucus carota subsp. sativus"
            assembly_level  — e.g. "Chromosome"
            assembly_name   — e.g. "DH1 v3.0"

    Raises:
        ValueError: If organism not found in NCBI Taxonomy (empty results).
        RuntimeError: On HTTP errors.
    """
    taxon = urllib.parse.quote(organism)
    params = {
        "returned_content": "ASSM_ACC",
        "filters.assembly_source": "refseq" if refseq_only else "all",
        "page_size": str(page_size),
    }
    url = _build_url(f"/genome/taxon/{taxon}/dataset_report", params)

    logger.debug(f"GET {url}")

    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"NCBI API error {e.code}: {body}") from e

    reports = data.get("reports", [])
    if not reports:
        raise ValueError(
            f"No assemblies found for '{organism}'. "
            "The name may not be a valid NCBI Taxonomy name. "
            "Try a taxon ID or use --accession with a known GCF/GCA accession."
        )

    results = []
    for rep in reports:
        results.append({
            "accession": rep.get("accession", ""),
            "current_accession": rep.get("current_accession", rep.get("accession", "")),
            "organism_name": rep.get("organism", {}).get("organism_name", ""),
            "assembly_level": rep.get("assembly_info", {}).get("assembly_level", ""),
            "assembly_name": rep.get("assembly_info", {}).get("assembly_name", ""),
        })
    return results


def download_protein_fasta(
    accession: str,
    output_fasta: str | Path,
) -> Path:
    """Download protein FASTA for a genome assembly from NCBI Datasets.

    Downloads the assembly ZIP (which contains protein.faa among other
    metadata), extracts just the protein.faa, and writes it to *output_fasta*.

    Args:
        accession: NCBI assembly accession with version (e.g. "GCF_001605985.2").
        output_fasta: Path to write the extracted protein.faa.

    Returns:
        Path to the written FASTA file.

    Raises:
        RuntimeError: On HTTP errors or if protein.faa not found in ZIP.
    """
    output_fasta = Path(output_fasta)
    output_fasta.parent.mkdir(parents=True, exist_ok=True)

    params = {"include_annotation_type": "PROT_FASTA"}
    url = _build_url(f"/genome/accession/{accession}/download", params)

    logger.info(f"Downloading protein FASTA for {accession}...")
    logger.debug(f"GET {url}")

    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            zip_bytes = resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"NCBI API error {e.code}: {body}") from e

    # Extract protein.faa from the ZIP
    expected_path = f"ncbi_dataset/data/{accession}/protein.faa"
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        # Try exact path first, then fall back to any protein.faa
        target = None
        if expected_path in zf.namelist():
            target = expected_path
        else:
            for name in zf.namelist():
                if name.endswith("protein.faa"):
                    target = name
                    break

        if target is None:
            available = "\n  ".join(zf.namelist()[:20])
            raise RuntimeError(
                f"protein.faa not found in ZIP. Available files:\n  {available}"
            )

        logger.debug(f"Extracting {target} from ZIP...")
        protein_bytes = zf.read(target)

    output_fasta.write_bytes(protein_bytes)
    size_mb = output_fasta.stat().st_size / (1024 * 1024)

    # Count proteins
    n_proteins = sum(1 for line in output_fasta.read_text().splitlines() if line.startswith(">"))

    logger.info(
        f"Downloaded {output_fasta} ({size_mb:.1f} MB, {n_proteins} proteins)",
        extra={"output_path": output_fasta, "size_mb": size_mb, "count": n_proteins},
    )
    return output_fasta


def fetch(
    organism: str | None = None,
    accession: str | None = None,
    output_fasta: str | Path = "data/input/proteins.faa",
) -> Path:
    """High-level fetch: search by organism or download by accession.

    Exactly one of *organism* or *accession* must be provided.
    If *organism* is given, searches NCBI and downloads the first result.

    Args:
        organism: Scientific name or taxon ID (searches NCBI).
        accession: Assembly accession (downloads directly).
        output_fasta: Output path for the protein FASTA.

    Returns:
        Path to the written FASTA file.
    """
    if accession and organism:
        raise ValueError("Provide either --accession or --organism, not both.")
    if not accession and not organism:
        raise ValueError("Must provide either --accession or --organism.")

    if accession:
        return download_protein_fasta(accession, output_fasta)

    # Search by organism (guaranteed non-None by validation above)
    assert organism is not None
    logger.info(f"Searching NCBI for assemblies of '{organism}'...")
    results = search_assemblies(organism)

    logger.info(f"Found {len(results)} assembly(ies)")
    for i, r in enumerate(results):
        logger.info(
            f"  [{i}] {r['current_accession']}  "
            f"{r['organism_name']}  "
            f"({r['assembly_level']}, {r['assembly_name']})"
        )

    first = results[0]
    logger.info(f"Downloading first result: {first['current_accession']}")
    return download_protein_fasta(first["current_accession"], output_fasta)
