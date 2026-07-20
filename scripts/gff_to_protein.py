#!/usr/bin/env python3
"""Extract protein FASTA from GFF3 annotation + genome FASTA.

Pure Python (pyfaidx for genome access, manual GFF parsing for speed).

Usage:
    uv run python scripts/gff_to_protein.py \
        --gff data/genomes/d_crumenatum/D8/D8.protein.best.gff \
        --genome data/genomes/d_crumenatum/D8/D8.genome.fasta \
        --output data/genomes/d_crumenatum/D8/D8.protein.faa
"""

import argparse
from collections import defaultdict
from pathlib import Path

from pyfaidx import Fasta


# Standard genetic code
CODON_TABLE = {
    'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L',
    'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
    'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*',
    'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W',
    'CTT': 'L', 'CTC': 'L', 'CTA': 'L', 'CTG': 'L',
    'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
    'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q',
    'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
    'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M',
    'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',
    'AAT': 'N', 'AAC': 'N', 'AAA': 'K', 'AAG': 'K',
    'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
    'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V',
    'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',
    'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
    'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G',
}

COMPLEMENT = str.maketrans('ATCGatcg', 'TAGCtagc')


def rc(seq: str) -> str:
    return seq.translate(COMPLEMENT)[::-1]


def translate(seq: str) -> str:
    protein = []
    for i in range(0, len(seq) - 2, 3):
        protein.append(CODON_TABLE.get(seq[i:i+3].upper(), 'X'))
    return ''.join(protein)


def parse_gff_cds(gff_path: str) -> dict[str, list]:
    """Parse GFF, return {mRNA_id: [(seqid, start, end, strand, phase)]} for CDS features.

    Uses dict-of-lists for speed (no database). ~32 MB GFF parsed in seconds.
    """
    mrna_cds: dict[str, list] = defaultdict(list)
    n_genes = 0
    n_mrnas = 0
    n_cds = 0

    with open(gff_path) as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            cols = line.split('\t')
            if len(cols) < 9:
                continue
            feat = cols[2]
            attrs = cols[8]

            if feat == 'gene':
                n_genes += 1
            elif feat == 'mRNA':
                n_mrnas += 1
            elif feat == 'CDS':
                n_cds += 1
                # Extract Parent ID
                parent = None
                for attr in attrs.split(';'):
                    if attr.startswith('Parent='):
                        parent = attr.split('=', 1)[1]
                        break
                if parent:
                    mrna_cds[parent].append((
                        cols[0],                    # seqid
                        int(cols[3]),               # start (1-based)
                        int(cols[4]),               # end (1-based)
                        cols[6],                    # strand
                        int(cols[7]) if cols[7] != '.' else 0,  # phase
                    ))

    print(f"  {n_genes} genes, {n_mrnas} mRNAs, {n_cds} CDS features")
    print(f"  {len(mrna_cds)} mRNAs with CDS features")
    return mrna_cds


def extract_proteins(
    gff_path: str | Path,
    genome_path: str | Path,
) -> dict[str, str]:
    """Extract protein sequences from GFF + genome.

    Note on GFF3 phase: the phase field in this GFF (EVM predictions)
    does not need to be applied — the CDS feature boundaries already
    encode in-frame concatenation. Applying the phase values here
    introduces frame shifts. We ignore phase and concatenate raw CDS
    sequences (RC'd for - strand), then translate.
    """
    print(f"Loading genome from {genome_path}...")
    genome = Fasta(str(genome_path))
    print(f"  {len(genome.keys())} scaffolds loaded")

    print(f"Parsing GFF from {gff_path}...")
    mrna_cds = parse_gff_cds(str(gff_path))

    proteins: dict[str, str] = {}
    n_skipped = 0

    for mrna_id, cds_list in mrna_cds.items():
        # Sort CDS by genomic position for transcription direction
        if cds_list[0][3] == '+':
            cds_list.sort(key=lambda x: x[1])    # ascending for + strand
        else:
            cds_list.sort(key=lambda x: -x[1])    # descending for - strand

        # Extract and concatenate CDS (ignoring phase — CDS boundaries
        # from this annotation already encode correct in-frame translation)
        nuc_parts = []
        for seqid, start, end, strand, _phase in cds_list:
            try:
                seq = genome[seqid][start - 1:end]  # pyfaidx uses 0-based half-open
            except KeyError:
                n_skipped += 1
                nuc_parts = []
                break

            seq = str(seq)
            if strand == '-':
                seq = rc(seq)

            nuc_parts.append(seq)

        if not nuc_parts:
            continue

        full_cds = ''.join(nuc_parts)

        if len(full_cds) < 30:
            n_skipped += 1
            continue

        protein = translate(full_cds)
        # Remove terminal stop codon
        if protein.endswith('*'):
            protein = protein[:-1]

        if len(protein) >= 10:
            proteins[mrna_id] = protein

    print(f"  {len(proteins)} proteins extracted")
    if n_skipped:
        print(f"  {n_skipped} entries skipped")

    return proteins


def main():
    parser = argparse.ArgumentParser(
        description="Extract protein FASTA from GFF3 + genome"
    )
    parser.add_argument('--gff', required=True)
    parser.add_argument('--genome', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    proteins = extract_proteins(args.gff, args.genome)

    # Verify vs gffread: sample a few proteins
    with open(args.output, 'w') as f:
        for mrna_id, seq in proteins.items():
            f.write(f">{mrna_id}\n")
            for i in range(0, len(seq), 60):
                f.write(seq[i:i+60] + '\n')

    print(f"\nWrote {len(proteins)} proteins to {args.output}")

    # Quick validation
    with_stop = sum(1 for s in proteins.values() if '*' in s)
    print(f"  Internal stop codons: {with_stop} ({with_stop/len(proteins)*100:.1f}%)")


if __name__ == '__main__':
    main()
