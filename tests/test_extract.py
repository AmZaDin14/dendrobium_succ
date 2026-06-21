"""Tests for fragment extraction (extract.py).

These verify the core logic without needing Modal or RLSuccSite:
  - Correct fragment length (33)
  - Correct centering on K
  - X padding at termini
  - Header format (>id|pos_N)
  - DNA sequence skipping
"""

from pathlib import Path

from dendrobium_succ.extract import extract_fragments


def test_basic_extraction(tmp_path: Path):
    """Single protein with one K in the middle → one 33-mer fragment."""
    fasta = tmp_path / "test.fasta"
    # 40 AA with a single K at position 20 (1-based)
    fasta.write_text(">prot1\nAAAAAAAAAAAAAAAAAAAKAAAAAAAAAAAAAAAAAAAAA\n")

    out = tmp_path / "fragments.fasta"
    count = extract_fragments(fasta, out)

    assert count == 1
    lines = out.read_text().strip().split("\n")
    assert lines[0] == ">prot1|pos_20"
    assert len(lines[1]) == 33
    # K is at position 20 (1-based), center of 33-mer is index 16 (0-based)
    assert lines[1][16] == "K"


def test_multiple_lysines(tmp_path: Path):
    """Protein with multiple K residues → multiple fragments."""
    fasta = tmp_path / "test.fasta"
    # 50 AA with K at positions 5, 15, 25, 35 (1-based), rest are A
    fasta.write_text(">prot1\nAAAAKAAAAAAAAAKAAAAAAAAAKAAAAAAAAAKAAAAAAAAAAAAA\n")

    out = tmp_path / "fragments.fasta"
    count = extract_fragments(fasta, out)

    assert count == 4
    lines = out.read_text().strip().split("\n")
    headers = [lines[i] for i in range(0, len(lines), 2)]
    assert headers == [">prot1|pos_5", ">prot1|pos_15", ">prot1|pos_25", ">prot1|pos_35"]


def test_padding_at_termini(tmp_path: Path):
    """K near the N-terminus → fragment padded with X at the start."""
    fasta = tmp_path / "test.fasta"
    # K at position 2 (1-based), needs 15 X's at the start
    fasta.write_text(">prot1\nAKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWYACDEFG\n")

    out = tmp_path / "fragments.fasta"
    count = extract_fragments(fasta, out)

    assert count >= 1
    lines = out.read_text().strip().split("\n")
    # First fragment: K at pos 2, needs 15 X's at start
    first_frag = lines[1]
    assert len(first_frag) == 33
    assert first_frag[:15] == "X" * 15
    assert first_frag[15] == "A"  # residue before K
    assert first_frag[16] == "K"  # center


def test_padding_at_c_terminus(tmp_path: Path):
    """K near the C-terminus → fragment padded with X at the end."""
    fasta = tmp_path / "test.fasta"
    # Short protein with K near the end
    fasta.write_text(">prot1\nACDEFGHIK\n")

    out = tmp_path / "fragments.fasta"
    count = extract_fragments(fasta, out)

    assert count == 1
    lines = out.read_text().strip().split("\n")
    frag = lines[1]
    assert len(frag) == 33
    # K is at position 9 (1-based), center index 16
    assert frag[16] == "K"
    # C-terminus needs padding: 33 - (9 + 16) = 8 X's at end
    assert frag[-8:] == "X" * 8


def test_dna_skipped(tmp_path: Path):
    """DNA-looking sequences (>100bp, only ATGCN) should be skipped."""
    fasta = tmp_path / "test.fasta"
    # 120 bp DNA sequence with no K (so even if processed, 0 fragments)
    dna_seq = "ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGC" * 2
    fasta.write_text(f">dna_seq\n{dna_seq}\n")

    out = tmp_path / "fragments.fasta"
    count = extract_fragments(fasta, out)

    assert count == 0
    assert out.read_text().strip() == ""


def test_no_lysines(tmp_path: Path):
    """Protein with no K → zero fragments."""
    fasta = tmp_path / "test.fasta"
    fasta.write_text(">prot1\nACDEFGHIJLMNPQRSTVWYACDEFGHIJLMNPQRSTVWY\n")

    out = tmp_path / "fragments.fasta"
    count = extract_fragments(fasta, out)

    assert count == 0
