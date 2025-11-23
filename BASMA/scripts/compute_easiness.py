#!/usr/bin/env python3

import csv
import json
import argparse
from pathlib import Path
from typing import Dict, Tuple

# Default config path (BASMA directory, one level up from scripts/)
DEFAULT_CONFIG = Path(__file__).parent.parent / 'config' / 'config.json'


def load_config(config_path: Path) -> dict:
    """Load configuration from JSON file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with config_path.open('r') as f:
        return json.load(f)


def parse_temp_scoring(temp_csv: Path, config: dict) -> Dict[Tuple[str, str, str, str, str], Tuple[int, str]]:
    """Parse Temp CSV to extract (ASim, FSim, DFreq, DCom, RCom) -> (Score, Category) mappings."""
    combo_to_score = {}
    
    if not temp_csv.exists():
        raise SystemExit(f"Temp file not found: {temp_csv}")
    
    scoring_cfg = config['scoring_table']
    header_row = scoring_cfg['header_row']  # 0-indexed, so row 13 = index 12
    data_start = scoring_cfg['data_start_row']  # 0-indexed, so row 14 = index 13
    cols = scoring_cfg['columns']
    thresholds = config['category_thresholds']
    
    with temp_csv.open('r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
        if len(rows) < data_start:
            raise SystemExit(f"Temp file doesn't have expected structure (need at least {data_start} rows)")
        
        # Data starts at data_start (index data_start-1)
        for i in range(data_start - 1, len(rows)):
            row = rows[i]
            if len(row) < max(cols.values()) + 1:
                continue
            
            asim = row[cols['asim']].strip() if len(row) > cols['asim'] else ''
            fsim = row[cols['fsim']].strip() if len(row) > cols['fsim'] else ''
            dfreq = row[cols['dfreq']].strip() if len(row) > cols['dfreq'] else ''
            dcom = row[cols['dcom']].strip() if len(row) > cols['dcom'] else ''
            rcom = row[cols['rcom']].strip() if len(row) > cols['rcom'] else ''
            score_str = row[cols['score']].strip() if len(row) > cols['score'] else ''
            category = row[cols['category']].strip() if len(row) > cols['category'] else ''
            
            # Skip empty rows
            if not asim or not fsim or not dfreq or not dcom or not rcom:
                continue
            
            # Validate levels
            if asim not in ('S', 'D') or fsim not in ('S', 'D'):
                continue
            if dfreq not in ('L', 'M', 'H') or dcom not in ('L', 'M', 'H') or rcom not in ('L', 'M', 'H'):
                continue
            
            try:
                score = int(score_str)
            except ValueError:
                continue
            
            key = (asim, fsim, dfreq, dcom, rcom)
            if category:
                combo_to_score[key] = (score, category)
            else:
                # If no category specified, infer from score ranges using config thresholds
                if score >= thresholds['easy_min']:
                    category = 'Easy'
                elif score >= thresholds['medium_min']:
                    category = 'Medium'
                else:
                    category = 'Hard'
                combo_to_score[key] = (score, category)
    
    return combo_to_score


def map_asim(asim_raw: str) -> str:
    try:
        return 'S' if int(asim_raw) == 1 else 'D'
    except Exception:
        return 'D' if (asim_raw or '').strip() not in ('1', 'S') else 'S'


def map_fsim(fsim_raw: str) -> str:
    try:
        return 'S' if int(fsim_raw) == 1 else 'D'
    except Exception:
        return 'D' if (fsim_raw or '').strip() not in ('1', 'S') else 'S'


def map_dfreq(dfreq_raw: str, config: dict) -> str:
    """Map DFreq rounded log to L/M/H using config thresholds."""
    thresholds = config['mapping_thresholds']['dfreq']
    try:
        rl = int(str(dfreq_raw).strip())
    except Exception:
        return ''
    if rl <= thresholds['low_max']:
        return 'L'
    if rl <= thresholds['medium_max']:
        return 'M'
    return 'H'


def map_dcom(dcom_raw: str, config: dict) -> str:
    """Map DCom pop count to L/M/H using config thresholds."""
    thresholds = config['mapping_thresholds']['dcom']
    try:
        pc = int(str(dcom_raw).strip())
    except Exception:
        return ''
    if pc <= thresholds['low_max']:
        return 'L'
    if pc <= thresholds['medium_max']:
        return 'M'
    return 'H'


def map_rcom(rcom_raw: str, config: dict) -> str:
    """Map RCom pop count to L/M/H using config thresholds."""
    thresholds = config['mapping_thresholds']['rcom']
    try:
        pc = int(str(rcom_raw).strip())
    except Exception:
        return ''
    if pc <= thresholds['low_max']:
        return 'L'
    if pc <= thresholds['medium_max']:
        return 'M'
    return 'H'


def load_rcom_lookup(frequencies_csv: Path, config: dict) -> Dict[Tuple[str, str, str, str, str], str]:
    """Load RCom values from frequencies file, keyed by (English, French, MSA, POS, CODA)."""
    rcom_lookup = {}
    
    if not frequencies_csv.exists():
        print(f"Warning: Frequencies file not found: {frequencies_csv}")
        return rcom_lookup
    
    cols = config['frequencies_file']['columns']
    
    with frequencies_csv.open('r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header
        
        for row in reader:
            if len(row) < max(cols.values()) + 1:
                continue
            
            key = (
                row[cols['english']].strip() if len(row) > cols['english'] else '',
                row[cols['french']].strip() if len(row) > cols['french'] else '',
                row[cols['msa']].strip() if len(row) > cols['msa'] else '',
                row[cols['pos']].strip() if len(row) > cols['pos'] else '',
                row[cols['coda']].strip() if len(row) > cols['coda'] else ''
            )
            rcom_value = row[cols['rcom']].strip() if len(row) > cols['rcom'] else ''
            if rcom_value and all(key):  # Only add if all key components are non-empty
                rcom_lookup[key] = rcom_value
    
    return rcom_lookup


def main():
    parser = argparse.ArgumentParser(description='Compute easiness scores for BASMA words')
    parser.add_argument('--config', type=str, default=str(DEFAULT_CONFIG),
                       help='Path to configuration file')
    args = parser.parse_args()
    
    # Load config
    config_path = Path(args.config)
    config = load_config(config_path)
    
    # Get file paths from config (BASMA directory, one level up from scripts/)
    root = Path(__file__).parent.parent
    files = config['files']
    scores_csv = root / files['intermediate']['scores']
    frequencies_csv = root / files['intermediate']['frequencies']
    temp_csv = root / files['intermediate']['scoring_table']
    output_csv = root / files['output']['easiness']
    
    if not scores_csv.exists():
        raise SystemExit(f"Scores file not found: {scores_csv}")
    
    # Load scoring dictionary from Temp file
    combo_to_score = parse_temp_scoring(temp_csv, config)
    print(f"Loaded {len(combo_to_score)} scoring combinations from scoring table")
    
    # Load RCom lookup from frequencies file
    rcom_lookup = load_rcom_lookup(frequencies_csv, config)
    print(f"Loaded {len(rcom_lookup)} RCom entries from frequencies file")
    
    with scores_csv.open('r', newline='', encoding='utf-8') as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = list(reader.fieldnames or [])
        
        # Reorder columns: insert RCom right after DCom, and RComLevel after DComLevel
        out_fieldnames = []
        for col in fieldnames:
            out_fieldnames.append(col)
            # Insert RCom right after DCom
            if col == 'DCom':
                out_fieldnames.append('RCom')
        
        # Add remaining extra columns
        extra_cols = ['ASimLevel', 'FSimLevel', 'DFreqLevel', 'DComLevel', 'EasinessScore', 'EasinessCategory']
        for col in extra_cols:
            if col not in out_fieldnames:
                out_fieldnames.append(col)
                # Insert RComLevel right after DComLevel
                if col == 'DComLevel' and 'RComLevel' not in out_fieldnames:
                    out_fieldnames.append('RComLevel')
        
        # Make sure RComLevel is added if DComLevel was already present
        if 'DComLevel' in out_fieldnames and 'RComLevel' not in out_fieldnames:
            dcomlevel_idx = out_fieldnames.index('DComLevel')
            out_fieldnames.insert(dcomlevel_idx + 1, 'RComLevel')
        
        with output_csv.open('w', newline='', encoding='utf-8') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=out_fieldnames)
            writer.writeheader()
            
            for row in reader:
                asim_level = map_asim(row.get('ASim', ''))
                fsim_level = map_fsim(row.get('FSim', ''))
                dfreq_level = map_dfreq(row.get('DFreq', ''), config)
                dcom_level = map_dcom(row.get('DCom', ''), config)
                
                # Get RCom from lookup
                lookup_key = (
                    row.get('English', '').strip(),
                    row.get('French', '').strip(),
                    row.get('MSA', '').strip(),
                    row.get('POS', '').strip(),
                    row.get('CODA', '').strip()
                )
                rcom_raw = rcom_lookup.get(lookup_key, '')
                rcom_level = map_rcom(rcom_raw, config) if rcom_raw else ''
                
                # Use 5-factor key: (ASim, FSim, DFreq, DCom, RCom)
                key = (asim_level, fsim_level, dfreq_level, dcom_level, rcom_level)
                score_cat = combo_to_score.get(key)
                if score_cat is None:
                    easiness_score = ''
                    easiness_cat = ''
                else:
                    easiness_score, easiness_cat = score_cat
                
                row['ASimLevel'] = asim_level
                row['FSimLevel'] = fsim_level
                row['DFreqLevel'] = dfreq_level
                row['DComLevel'] = dcom_level
                row['RCom'] = rcom_raw  # Raw numeric RCom value
                row['RComLevel'] = rcom_level  # Mapped to L/M/H
                row['EasinessScore'] = easiness_score
                row['EasinessCategory'] = easiness_cat
                
                writer.writerow(row)
    
    print(f"Wrote: {output_csv}")


if __name__ == '__main__':
    main()
