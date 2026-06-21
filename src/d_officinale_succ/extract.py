"""Extract 33-mer fragments centered on each lysine (K) residue from a protein FASTA.

This reimplements RLSuccSite's Utils/extract_sites.py with a clean, importable
function. The output FASTA format must match exactly what RLSuccSite's Predict.py
expects:

    >{protein_id}|pos_{position_1based}
    {33-char fragment with X padding at termini}

The center residue (index 16, 0-based) of each fragment is the lysine of interest.
"""

from pathlib import Path

from Bio import SeqIO
from rich.console import Console

console = Console()

WINDOW_SIZE = 33


def extract_fragments(
    input_fasta: str | Path,
    output_fasta: str | Path,
    window_size: int = WINDOW_SIZE,
) -> int:
    """Extract fixed-length fragments centered on each lysine (K).

    For each K residue in each protein sequence, a window of *window_size*
    residues is extracted, centered on the K. If the K is near a terminus,
    the fragment is padded with 'X' characters to maintain the fixed length.

    DNA-looking sequences (only ATGCN, length > 100) are skipped with a warning.

    Args:
        input_fasta: Path to input protein FASTA (.faa / .fasta).
        output_fasta: Path to write the fragments FASTA.
        window_size: Fragment length (must be odd). Default 33.

    Returns:
        Number of fragments extracted (total K sites found).
    """
    half = window_size // 2
    count = 0

    with open(output_fasta, "w") as out:
        for record in SeqIO.parse(str(input_fasta), "fasta"):
            seq = str(record.seq).upper()

            # Skip sequences that look like DNA
            if len(seq) > 100 and all(c in "ATGCN" for c in seq[:100]):
                console.print(
                    f"[yellow]Warning:[/yellow] {record.id} looks like DNA — "
                    "skipping (model requires protein sequences)."
                )
                continue

            for i, res in enumerate(seq):
                if res != "K":
                    continue

                left = max(0, i - half)
                right = min(len(seq), i + half + 1)
                fragment = seq[left:right]

                # Pad with 'X' at the N-terminus
                if i < half:
                    fragment = "X" * (half - i) + fragment
                # Pad with 'X' at the C-terminus
                if (len(seq) - 1 - i) < half:
                    fragment = fragment + "X" * (half - (len(seq) - 1 - i))

                out.write(f">{record.id}|pos_{i + 1}\n{fragment}\n")
                count += 1

    console.print(f"[green]Extracted {count} lysine (K) sites[/green] → {output_fasta}")
    return count
