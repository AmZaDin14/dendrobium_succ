"""d_officinale_succ: Reproducible succinylation site prediction for Daucus officinale.

Wraps RLSuccSite's inference pipeline into a clean, reproducible harness:
  1. Extract 33-mer fragments around each lysine (K) from a protein FASTA
  2. Embed fragments with ProtT5-XL on Modal GPU
  3. Run RLSuccSite ensemble prediction (ProtT5 + TPEMPPS_CCP)
"""

__version__ = "0.1.0"
