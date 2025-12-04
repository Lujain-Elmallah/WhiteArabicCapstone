#!/usr/bin/env python3

import csv
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set

DEFAULT_CONFIG = Path(__file__).parent / 'config.json'

CATEGORIES = {'Easy', 'Medium', 'Hard'}


def load_config(config_path: Path) -> dict:
    """Load configuration from JSON file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with config_path.open('r') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description='Generate long-form files with all words by category')
    parser.add_argument('--config', type=str, default=str(DEFAULT_CONFIG),
                       help='Path to configuration file')
    args = parser.parse_args()
    
    # Load config
    config = load_config(Path(args.config))
    
    # Get file paths from config
    root = Path(__file__).parent
    easiness_csv = root / config['files']['output']['easiness']
    output_all = root / config['files']['output']['targets_all_long']
    output_triplet = root / config['files']['output']['targets_all_triplets']
    
    if not easiness_csv.exists():
        raise SystemExit(f"Easiness file not found: {easiness_csv}")

    rows = []
    by_id_to_cats: Dict[str, Set[str]] = {}

    with easiness_csv.open('r', newline='', encoding='utf-8') as f_in:
        reader = csv.DictReader(f_in)
        for r in reader:
            cat = r.get('EasinessCategory', '')
            if cat not in CATEGORIES:
                continue
            concept_id = r.get('ID', '')
            by_id_to_cats.setdefault(concept_id, set()).add(cat)
            rows.append({
                'ID': concept_id,
                'English': r.get('English', ''),
                'French': r.get('French', ''),
                'MSA': r.get('MSA', ''),
                'POS': r.get('POS', ''),
                'Category': cat,
                'CODA': r.get('CODA', ''),
                'Region': r.get('Region', ''),
                'ASimLevel': r.get('ASimLevel', ''),
                'FSimLevel': r.get('FSimLevel', ''),
                'DFreqLevel': r.get('DFreqLevel', ''),
                'DComLevel': r.get('DComLevel', ''),
                'EasinessScore': r.get('EasinessScore', ''),
            })

    fieldnames = [
        'ID', 'English', 'French', 'MSA', 'POS',
        'Category', 'CODA', 'Region',
        'ASimLevel', 'FSimLevel', 'DFreqLevel', 'DComLevel',
        'EasinessScore',
    ]

    # Write the full long-form file (all IDs, whatever categories they have)
    with output_all.open('w', newline='', encoding='utf-8') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # Write the long-form filtered to IDs that have all three categories
    valid_ids = {cid for cid, cats in by_id_to_cats.items() if CATEGORIES.issubset(cats)}

    with output_triplet.open('w', newline='', encoding='utf-8') as f_out2:
        writer = csv.DictWriter(f_out2, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            if r['ID'] in valid_ids:
                writer.writerow(r)

    print(f"Wrote: {output_all}")
    print(f"Wrote: {output_triplet} (IDs with all three categories)")


if __name__ == '__main__':
    main()
