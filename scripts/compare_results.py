#!/usr/bin/env python3
"""Compare our predictions with the original RLSuccSite results."""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

def compare_predictions(
    our_csv: str = "data/processed/full/predictions.csv",
    original_csv: str = "../RLSuccSite/results.csv"
):
    """Compare prediction results between our pipeline and original RLSuccSite."""
    
    print("=" * 80)
    print("COMPARING PREDICTIONS")
    print("=" * 80)
    
    # Load predictions
    print("\nLoading predictions...")
    our_df = pd.read_csv(our_csv)
    original_df = pd.read_csv(original_csv)
    
    print(f"Our predictions:      {len(our_df):,} rows")
    print(f"Original predictions: {len(original_df):,} rows")
    
    # Check if counts match
    if len(our_df) != len(original_df):
        print(f"\n⚠️  WARNING: Row counts differ by {abs(len(our_df) - len(original_df))}")
    
    # Check SequenceID alignment
    print("\nChecking SequenceID alignment...")
    if list(our_df['SequenceID']) == list(original_df['SequenceID']):
        print("✓ SequenceIDs match perfectly")
        ids_match = True
    else:
        print("⚠️  SequenceIDs do not match - comparing by position")
        ids_match = False
    
    # Compare PositiveProbability
    print("\nComparing PositiveProbability...")
    prob_diff = np.abs(our_df['PositiveProbability'] - original_df['PositiveProbability'])
    
    print(f"  Max difference:    {prob_diff.max():.6f}")
    print(f"  Mean difference:   {prob_diff.mean():.6f}")
    print(f"  Median difference: {prob_diff.median():.6f}")
    print(f"  Std deviation:     {prob_diff.std():.6f}")
    
    # Count significant differences
    sig_diff_001 = (prob_diff > 0.01).sum()
    sig_diff_005 = (prob_diff > 0.05).sum()
    sig_diff_010 = (prob_diff > 0.10).sum()
    
    print(f"\n  Differences > 0.01: {sig_diff_001:,} ({sig_diff_001/len(our_df)*100:.2f}%)")
    print(f"  Differences > 0.05: {sig_diff_005:,} ({sig_diff_005/len(our_df)*100:.2f}%)")
    print(f"  Differences > 0.10: {sig_diff_010:,} ({sig_diff_010/len(our_df)*100:.2f}%)")
    
    # Compare PredictedLabel
    print("\nComparing PredictedLabel...")
    label_match = (our_df['PredictedLabel'] == original_df['PredictedLabel']).sum()
    label_mismatch = len(our_df) - label_match
    
    print(f"  Matching labels:     {label_match:,} ({label_match/len(our_df)*100:.2f}%)")
    print(f"  Mismatching labels:  {label_mismatch:,} ({label_mismatch/len(our_df)*100:.2f}%)")
    
    # Show some examples of mismatches
    if label_mismatch > 0 and label_mismatch <= 10:
        print("\n  Examples of label mismatches:")
        mismatches = our_df[our_df['PredictedLabel'] != original_df['PredictedLabel']]
        for idx, row in mismatches.head(5).iterrows():
            orig_label = original_df.loc[idx, 'PredictedLabel']
            orig_prob = original_df.loc[idx, 'PositiveProbability']
            print(f"    {row['SequenceID']}:")
            print(f"      Our:      label={row['PredictedLabel']}, prob={row['PositiveProbability']:.6f}")
            print(f"      Original: label={orig_label}, prob={orig_prob:.6f}")
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    our_positive = our_df['PredictedLabel'].sum()
    original_positive = original_df['PredictedLabel'].sum()
    
    print(f"\nPositive predictions:")
    print(f"  Our pipeline:      {our_positive:,} ({our_positive/len(our_df)*100:.2f}%)")
    print(f"  Original RLSuccSite: {original_positive:,} ({original_positive/len(original_df)*100:.2f}%)")
    print(f"  Difference:        {abs(our_positive - original_positive):,}")
    
    print(f"\nLabel agreement:     {label_match/len(our_df)*100:.4f}%")
    print(f"Max prob difference: {prob_diff.max():.6f}")
    
    # Verdict
    print("\n" + "=" * 80)
    if label_mismatch == 0 and prob_diff.max() < 0.01:
        print("✓ PERFECT MATCH - Results are identical")
    elif label_mismatch < 10 and prob_diff.max() < 0.05:
        print("✓ EXCELLENT MATCH - Results are nearly identical")
    elif label_mismatch < 100 and prob_diff.max() < 0.10:
        print("⚠️  GOOD MATCH - Minor differences, likely due to floating point precision")
    else:
        print("⚠️  SIGNIFICANT DIFFERENCES - Investigate further")
    print("=" * 80)
    
    return {
        'row_count_match': len(our_df) == len(original_df),
        'ids_match': ids_match,
        'label_agreement': label_match / len(our_df),
        'max_prob_diff': prob_diff.max(),
        'mean_prob_diff': prob_diff.mean(),
        'label_mismatches': label_mismatch,
        'our_positive': our_positive,
        'original_positive': original_positive,
    }

if __name__ == "__main__":
    if len(sys.argv) == 3:
        compare_predictions(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 1:
        compare_predictions()
    else:
        print("Usage: python compare_results.py [our_csv] [original_csv]")
        print("       python compare_results.py  # uses defaults")
        sys.exit(1)
