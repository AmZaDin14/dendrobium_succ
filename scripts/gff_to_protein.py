#!/usr/bin/env python3
"""Extract protein sequences from GFF3 + genome FASTA (no BioPython dependency).

Usage:
    python scripts/gff_to_protein.py \
        --gff data/genomes/d_crumenatum/D8/D8.protein.best.gff \
        --genome data/genomes/d_crumenatum/D8/D8.genome.fasta \
        --output data/genomes/d_crumenatum/D8/D8.protein.faa
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path


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

COMPLEMENT = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C',
              'a': 't', 't': 'a', 'c': 'g', 'g': 'g',
              'N': 'N', 'n': 'n'}


def reverse_complement(seq: str) -> str:
    return ''.join(COMPLEMENT.get(b, b) for b in reversed(seq))


def translate(seq: str) -> str:
    """Translate nucleotide sequence to protein."""
    protein = []
    for i in range(0, len(seq) - 2, 3):
        codon = seq[i:i+3].upper()
        aa = CODON_TABLE.get(codon, 'X')
        protein.append(aa)
    return ''.join(protein)


def load_genome(path: str | Path) -> dict[str, str]:
    """Load genome FASTA into dict {seq_id: sequence}."""
    genome: dict[str, str] = {}
    current_id = None
    current_seq: list[str] = []

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('>'):
                if current_id:
                    genome[current_id] = ''.join(current_seq)
                current_id = line[1:].split()[0]  # first word after >
                current_seq = []
            else:
                current_seq.append(line.upper())

    if current_id and current_seq:
        genome[current_id] = ''.join(current_seq)

    return genome


def load_gff_cds(path: str | Path) -> dict[str, list[dict]]:
    """Parse GFF file, return {mRNA_id: [CDS features]}."""
    mrna_cds: dict[str, list[dict]] = defaultdict(list)
    gene_count = 0
    mrna_count = 0
    cds_count = 0

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            cols = line.split('\t')
            if len(cols) < 9:
                continue

            feat_type = cols[2]

            if feat_type == 'gene':
                gene_count += 1
            elif feat_type == 'mRNA':
                mrna_count += 1
            elif feat_type == 'CDS':
                attributes = cols[8]
                parent = ''
                for attr in attributes.split(';'):
                    if attr.startswith('Parent='):
                        parent = attr.split('=', 1)[1]
                        break

                if parent:
                    mrna_cds[parent].append({
                        'seqid': cols[0],
                        'start': int(cols[3]),
                        'end': int(cols[4]),
                        'strand': cols[6],
                        'phase': int(cols[7]) if cols[7] != '.' else 0,
                    })
                    cds_count += 1

    print(f"  {gene_count} genes, {mrna_count} mRNAs, {cds_count} CDS features")
    print(f"  {len(mrna_cds)} mRNAs with CDS features")
    return mrna_cds


def extract_proteins(
    gff_path: str | Path,
    genome_path: str | Path,
) -> dict[str, str]:
    """Extract protein sequences from GFF + genome.

    Returns:
        dict mapping mRNA_id → protein_sequence
    """
    print(f"Loading genome from {genome_path}...")
    genome = load_genome(genome_path)
    total_bp = sum(len(s) for s in genome.values())
    print(f"  {len(genome)} scaffolds loaded ({total_bp / 1e9:.2f} Gb)")

    print(f"Parsing GFF from {gff_path}...")
    mrna_cds = load_gff_cds(gff_path)

    proteins: dict[str, str] = {}
    skipped_no_seq = 0
    skipped_short = 0

    for mrna_id, cds_list in mrna_cds.items():
        # Sort CDS by position
        if cds_list[0]['strand'] == '+':
            cds_list.sort(key=lambda x: x['start'])
        else:
            cds_list.sort(key=lambda x: -x['start'])

        # Extract CDS nucleotides
        cds_nucs: list[str] = []
        phase = 0
        for cds in cds_list:
            scaffold = cds['seqid']
            if scaffold not in genome:
                skipped_no_seq += 1
                cds_nucs = []
                break

            start = cds['start'] - 1  # 0-based
            end = cds['end']
            seq = genome[scaffold][start:end]

            if cds['strand'] == '-':
                seq = reverse_complement(seq)

            # Apply phase
            seq = seq[phase:]
            if len(seq) >= 3:
                phase = (3 - len(seq) % 3) % 3

            cds_nucs.append(seq)

        if not cds_nucs:
            continue

        full_cds = ''.join(cds_nucs)

        if len(full_cds) < 3:
            skipped_short += 1
            continue

        protein = translate(full_cds)
        # Remove stop codon
        if protein.endswith('*'):
            protein = protein[:-1]

        if len(protein) >= 10:
            proteins[mrna_id] = protein

    print(f"  {len(proteins)} proteins extracted")
    if skipped_no_seq:
        print(f"  {skipped_no_seq} CDS skipped (scaffold not in genome)")
    if skipped_short:
        print(f"  {skipped_short} skipped (CDS too short)")

    return proteins


def main():
    parser = argparse.ArgumentParser(description="Extract protein FASTA from GFF3 + genome")
    parser.add_argument('--gff', required=True, help='GFF3 annotation file')
    parser.add_argument('--genome', required=True, help='Genome FASTA file')
    parser.add_argument('--output', required=True, help='Output protein FASTA')
    args = parser.parse_args()

    proteins = extract_proteins(args.gff, args.genome)

    with open(args.output, 'w') as f:
        for mrna_id, seq in proteins.items():
            # Derive gene ID from mRNA ID
            gene_id = mrna_id
            if '.m' in mrna_id:
                parts = mrna_id.split('.m')
                if len(parts) >= 2 and parts[1].isdigit():
                    gene_id = parts[0]
            f.write(f">{mrna_id} {gene_id}\n")
            # Wrap at 60 chars
            for i in range(0, len(seq), 60):
                f.write(seq[i:i+60] + '\n')

    print(f"\nWrote {len(proteins)} proteins to {args.output}")


if __name__ == '__main__':
    main()
