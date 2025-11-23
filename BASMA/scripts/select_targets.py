#!/usr/bin/env python3

import csv
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

DEFAULT_CONFIG = Path(__file__).parent.parent / 'config' / 'config.json'

LEVEL_ORDER = {'H': 3, 'M': 2, 'L': 1, '': 0}


def load_config(config_path: Path) -> dict:
    """Load configuration from JSON file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with config_path.open('r') as f:
        return json.load(f)


def parse_int_safe(value: str) -> Optional[int]:
    try:
        return int(str(value).replace(',', '').strip())
    except Exception:
        return None


def score_tuple(row: Dict[str, str]) -> Tuple[int, int, int]:
    # Primary: EasinessScore (higher is better for all categories)
    score = parse_int_safe(row.get('EasinessScore', '')) or -1
    # Tie-breakers: DComLevel (H>M>L), then DFreqLevel (H>M>L)
    dcom = LEVEL_ORDER.get(row.get('DComLevel', ''), 0)
    dfreq = LEVEL_ORDER.get(row.get('DFreqLevel', ''), 0)
    return (score, dcom, dfreq)


def pick_best(rows: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    if not rows:
        return None
    return max(rows, key=score_tuple)


def main():
    parser = argparse.ArgumentParser(description='Select best Easy/Medium/Hard words per concept')
    parser.add_argument('--config', type=str, default=str(DEFAULT_CONFIG),
                       help='Path to configuration file')
    args = parser.parse_args()
    
    # Load config
    config = load_config(Path(args.config))
    
    # Get file paths from config (BASMA directory, one level up from scripts/)
    root = Path(__file__).parent.parent
    easiness_csv = root / config['files']['output']['easiness']
    output_csv = root / config['files']['output']['targets']
    
    if not easiness_csv.exists():
        raise SystemExit(f"Easiness file not found: {easiness_csv}")

    by_id: Dict[str, List[Dict[str, str]]] = {}
    with easiness_csv.open('r', newline='', encoding='utf-8') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            by_id.setdefault(row.get('ID', ''), []).append(row)

    out_rows: List[Dict[str, str]] = []

    for concept_id, rows in by_id.items():
        # Partition by category
        easy_rows = [r for r in rows if r.get('EasinessCategory') == 'Easy']
        med_rows = [r for r in rows if r.get('EasinessCategory') == 'Medium']
        hard_rows = [r for r in rows if r.get('EasinessCategory') == 'Hard']

        best_easy = pick_best(easy_rows)
        best_med = pick_best(med_rows)
        best_hard = pick_best(hard_rows)

        if not (best_easy and best_med and best_hard):
            continue  # only keep IDs that have all three

        # Use shared concept metadata from any row (prefer easy row)
        meta = best_easy
        out_rows.append({
            'ID': concept_id,
            'English': meta.get('English', ''),
            'French': meta.get('French', ''),
            'MSA': meta.get('MSA', ''),
            'POS': meta.get('POS', ''),
            'EasyCODA': best_easy.get('CODA', ''),
            'EasyRegion': best_easy.get('Region', ''),
            'EasyEasinessScore': best_easy.get('EasinessScore', ''),
            'MediumCODA': best_med.get('CODA', ''),
            'MediumRegion': best_med.get('Region', ''),
            'MediumEasinessScore': best_med.get('EasinessScore', ''),
            'HardCODA': best_hard.get('CODA', ''),
            'HardRegion': best_hard.get('Region', ''),
            'HardEasinessScore': best_hard.get('EasinessScore', ''),
        })

    fieldnames = [
        'ID', 'English', 'French', 'MSA', 'POS',
        'EasyCODA', 'EasyRegion', 'EasyEasinessScore',
        'MediumCODA', 'MediumRegion', 'MediumEasinessScore',
        'HardCODA', 'HardRegion', 'HardEasinessScore',
    ]

    with output_csv.open('w', newline='', encoding='utf-8') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for r in sorted(out_rows, key=lambda x: int(x['ID'])):
            writer.writerow(r)

    print(f"Wrote: {output_csv} with {len(out_rows)} IDs")


if __name__ == '__main__':
    main()
