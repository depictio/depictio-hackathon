#!/usr/bin/env python3
"""
Simulate continuous image acquisition by appending rows to phenobase.csv.

This script works with REAL data - it truncates the CSV to a smaller subset,
then gradually appends back real rows with existing image files.

Usage:
    python scripts/simulate_stream.py --reset          # Reset to 20 rows
    python scripts/simulate_stream.py --interval 2     # Append 1 row every 2s
    python scripts/simulate_stream.py --interval 1 --batch 3  # Append 3 rows every 1s
"""

import argparse
import csv
import shutil
import time
from datetime import datetime
from pathlib import Path
import pandas as pd


BACKUP_SUFFIX = ".backup"


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Simulate streaming image acquisition')
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset CSV to initial subset (creates backup if needed)'
    )
    parser.add_argument(
        '--initial',
        type=int,
        default=20,
        help='Number of rows to keep on reset (default: 20)'
    )
    parser.add_argument(
        '--interval',
        type=float,
        default=2.0,
        help='Seconds between batches (default: 2.0)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=0,
        help='Total rows to add, 0=all remaining (default: 0)'
    )
    parser.add_argument(
        '--batch',
        type=int,
        default=1,
        help='Rows to add per batch (default: 1)'
    )
    parser.add_argument(
        '--csv',
        type=str,
        default='data/phenobase.csv',
        help='Path to phenobase CSV (default: data/phenobase.csv)'
    )
    return parser.parse_args()


def ensure_backup(csv_path):
    """Create backup of original CSV if it doesn't exist."""
    backup_path = Path(str(csv_path) + BACKUP_SUFFIX)
    if not backup_path.exists():
        shutil.copy(csv_path, backup_path)
        print(f"Created backup: {backup_path}")
    return backup_path


def reset_csv(csv_path, initial_rows):
    """Reset CSV to initial subset from backup."""
    backup_path = ensure_backup(csv_path)

    # Read backup (full data)
    with open(backup_path, 'r') as f:
        lines = f.readlines()

    # Keep header rows (first 2 lines) + initial_rows of data
    header_lines = lines[:2]
    data_lines = lines[2:2 + initial_rows]

    # Write truncated CSV
    with open(csv_path, 'w') as f:
        f.writelines(header_lines + data_lines)

    print(f"Reset {csv_path} to {initial_rows} data rows")
    return len(data_lines)


def get_remaining_rows(csv_path):
    """Get rows from backup that aren't in current CSV."""
    backup_path = Path(str(csv_path) + BACKUP_SUFFIX)
    if not backup_path.exists():
        print("No backup found. Run with --reset first.")
        return [], []

    # Read current CSV
    with open(csv_path, 'r') as f:
        current_lines = f.readlines()

    # Read backup
    with open(backup_path, 'r') as f:
        backup_lines = f.readlines()

    current_count = len(current_lines) - 2  # Subtract 2 header lines
    backup_count = len(backup_lines) - 2

    # Get remaining rows from backup
    remaining = backup_lines[2 + current_count:]  # Skip headers + current rows
    fieldnames = backup_lines[1].strip().split(',')

    return remaining, fieldnames


def append_rows(csv_path, rows):
    """Append raw CSV rows to file."""
    with open(csv_path, 'a') as f:
        for row in rows:
            if not row.endswith('\n'):
                row += '\n'
            f.write(row)


def parse_row_info(row_line, fieldnames):
    """Extract filename and pos from a CSV row line."""
    values = row_line.strip().split(',')
    row_dict = dict(zip(fieldnames, values))
    return {
        'filename': row_dict.get('czi_filename', 'unknown'),
        'pos': row_dict.get('pos', '?'),
    }


def main():
    """Main simulation loop."""
    args = parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        return

    # Handle reset mode
    if args.reset:
        ensure_backup(csv_path)
        reset_csv(csv_path, args.initial)
        print("\nReady to simulate. Run without --reset to start adding rows.")
        return

    # Get remaining rows to add
    remaining_rows, fieldnames = get_remaining_rows(csv_path)
    if not remaining_rows:
        print("No remaining rows to add. Run with --reset first.")
        return

    # Determine how many to add
    total_to_add = args.count if args.count > 0 else len(remaining_rows)
    total_to_add = min(total_to_add, len(remaining_rows))

    print("=" * 60)
    print("Image Stream Simulator (Real Data)")
    print("=" * 60)
    print(f"CSV: {csv_path}")
    print(f"Remaining rows available: {len(remaining_rows)}")
    print(f"Rows to add: {total_to_add}")
    print(f"Batch size: {args.batch}")
    print(f"Interval: {args.interval}s")
    print(f"Est. duration: ~{(total_to_add / args.batch) * args.interval:.1f}s")
    print("=" * 60)
    print("\nStarting simulation... (Press Ctrl+C to stop)")
    print()

    rows_added = 0
    try:
        while rows_added < total_to_add:
            # Get batch of rows
            batch_size = min(args.batch, total_to_add - rows_added)
            batch = remaining_rows[rows_added:rows_added + batch_size]

            # Append to CSV
            append_rows(csv_path, batch)

            # Show what was added
            for row_line in batch:
                info = parse_row_info(row_line, fieldnames)
                print(f"  Added: {info['filename']} (pos={info['pos']})")

            rows_added += batch_size
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Progress: {rows_added}/{total_to_add}")

            # Wait before next batch
            if rows_added < total_to_add:
                time.sleep(args.interval)

    except KeyboardInterrupt:
        print(f"\n\nStopped by user. Added {rows_added} rows total.")

    print("\n" + "=" * 60)
    print(f"Simulation complete: {rows_added} rows added")
    print("=" * 60)


if __name__ == '__main__':
    main()
