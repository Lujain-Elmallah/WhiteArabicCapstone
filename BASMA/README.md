# BASMA Easiness Computation Pipeline

A reproducible pipeline for computing easiness scores for Arabic dialectal words based on multiple linguistic features.

## Overview

This pipeline computes easiness scores for dialectal words using a 5-factor scoring system:
1. **ASim** (Arabic Similarity): Whether the dialectal word matches MSA after normalization
2. **FSim** (Foreign Similarity): Whether the dialectal word matches transliterations
3. **DFreq** (Dialect Frequency): Rounded log of dialectal word frequency
4. **DCom** (Dialect Commonality): Number of regions where the word is used
5. **RCom** (Root Commonality): Number of regions where the root is used

Words are categorized as **Easy**, **Medium**, or **Hard** based on their easiness scores.

## Pipeline Steps

1. **extract.py** - Extract features from MADAR lexicon (frequencies, similarities, regions, roots)
2. **compute_easiness.py** - Compute easiness scores using the 5-factor scoring system
3. **select_targets.py** - Select best Easy/Medium/Hard word per concept ID
4. **select_targets_all.py** - Generate long-form files with all words by category

## Quick Start

### Run the complete pipeline:

```bash
python run_pipeline.py
```

### Run individual steps:

```bash
# Step 1: Extract features
python extract.py

# Step 2: Compute easiness scores
python compute_easiness.py

# Step 3: Select best words per concept
python select_targets.py

# Step 4: Generate long-form files
python select_targets_all.py
```

### Skip extraction (use existing intermediate files):

```bash
python run_pipeline.py --skip-extract
```

## Configuration

All parameters are configurable via `config.json`. Key parameters:

### Mapping Thresholds

Control how raw values are mapped to L/M/H levels:

```json
"mapping_thresholds": {
  "dfreq": {
    "low_max": 1,      // 0-1 => L
    "medium_max": 4    // 2-4 => M, 5+ => H
  },
  "dcom": {
    "low_max": 1,      // 1 => L
    "medium_max": 3    // 2-3 => M, 4+ => H
  },
  "rcom": {
    "low_max": 1,      // 1 => L
    "medium_max": 3    // 2-3 => M, 4+ => H
  }
}
```

### Category Thresholds

Control how easiness scores map to categories:

```json
"category_thresholds": {
  "easy_min": 1000,    // >= 1000 => Easy
  "medium_min": 100    // >= 100 => Medium, < 100 => Hard
}
```

### File Paths

All input/output file paths are configurable:

```json
"files": {
  "input": {
    "madar_lexicon": "MADAR_Lexicon_v1.0.tsv",
    "msa_freq": "MSA_freq_lists.tsv",
    "da_freq": "DA_freq_lists.tsv",
    "transliteration": "MADAR_Lexicon_transliteration.tsv",
    "roots": "roots.tsv"
  },
  "intermediate": {
    "frequencies": "BASMA Plan - frequencies.csv",
    "scores": "BASMA Plan - Scores.csv",
    "scoring_table": "BASMA Plan - Temp (1).csv"
  },
  "output": {
    "easiness": "BASMA Easiness by Word.csv",
    "targets": "BASMA IDs with E-M-H.csv",
    "targets_all_long": "BASMA IDs with All E-M-H (long).csv",
    "targets_all_triplets": "BASMA IDs with All E-M-H (long, triplets only).csv"
  }
}
```

### Scoring Table Configuration

Configure how the scoring table CSV is parsed:

```json
"scoring_table": {
  "header_row": 13,        // Row number (1-indexed) where headers are
  "data_start_row": 14,    // Row number (1-indexed) where data starts
  "columns": {
    "asim": 3,
    "fsim": 4,
    "dfreq": 5,
    "dcom": 6,
    "rcom": 7,
    "score": 8,
    "category": 10
  }
}
```

## Output Files

### BASMA Easiness by Word.csv
Complete easiness scores for all words with all computed features.

### BASMA IDs with E-M-H.csv
One row per concept ID with the best Easy, Medium, and Hard word selected.

### BASMA IDs with All E-M-H (long).csv
All words from all concepts, organized by category.

### BASMA IDs with All E-M-H (long, triplets only).csv
All words from concepts that have all three categories (Easy, Medium, Hard).

## Customizing Parameters

To adjust the easiness scoring:

1. **Modify thresholds in config.json**:
   - Change `mapping_thresholds` to adjust L/M/H boundaries
   - Change `category_thresholds` to adjust Easy/Medium/Hard boundaries

2. **Update the scoring table**:
   - Modify `BASMA Plan - Temp (1).csv` to change scores for specific factor combinations
   - Update `scoring_table` config if the CSV structure changes

3. **Run the pipeline**:
   ```bash
   python run_pipeline.py
   ```

## Requirements

- Python 3.7+
- pandas
- numpy

Install dependencies:
```bash
pip install pandas numpy
```

## File Structure

```
BASMA/
├── config.json                    # Configuration file
├── run_pipeline.py                # Main pipeline script
├── extract.py                     # Feature extraction
├── compute_easiness.py            # Easiness computation
├── select_targets.py              # Best word selection
├── select_targets_all.py           # Long-form file generation
├── README.md                      # This file
├── MADAR_Lexicon_v1.0.tsv         # Input: MADAR lexicon
├── MSA_freq_lists.tsv             # Input: MSA frequencies
├── DA_freq_lists.tsv              # Input: Dialect frequencies
├── MADAR_Lexicon_transliteration.tsv  # Input: Transliterations
├── roots.tsv                      # Input: Root mappings
└── BASMA Plan - Temp (1).csv      # Input: Scoring table
```

## Notes

- The pipeline is designed to be reproducible: all parameters are in `config.json`
- Intermediate files can be reused by using `--skip-extract`
- All scripts accept `--config` to specify a custom config file
- Paths in config are relative to the script directory

