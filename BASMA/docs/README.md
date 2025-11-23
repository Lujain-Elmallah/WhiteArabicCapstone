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

## Directory Structure

```
BASMA/
├── scripts/              # Python scripts
│   ├── extract.py       # Feature extraction
│   ├── compute_easiness.py
│   ├── select_targets.py
│   ├── select_targets_all.py
│   └── run_pipeline.py  # Main pipeline runner
├── config/              # Configuration files
│   └── config.json      # Main configuration
├── data/
│   ├── input/           # Input data files (TSV, XLSX)
│   ├── intermediate/     # Intermediate processing files
│   └── output/          # Final output files (CSV)
└── docs/                # Documentation
    └── README.md        # This file
```

## Pipeline Steps

1. **extract.py** - Extract features from MADAR lexicon (frequencies, similarities, regions, roots)
2. **compute_easiness.py** - Compute easiness scores using the 5-factor scoring system
3. **select_targets.py** - Select best Easy/Medium/Hard word per concept ID
4. **select_targets_all.py** - Generate long-form files with all words by category

## Quick Start

### Run the complete pipeline:

From the BASMA directory:
```bash
cd BASMA
python scripts/run_pipeline.py
```

### Run individual steps:

```bash
# Step 1: Extract features
python scripts/extract.py

# Step 2: Compute easiness scores
python scripts/compute_easiness.py

# Step 3: Select best words per concept
python scripts/select_targets.py

# Step 4: Generate long-form files
python scripts/select_targets_all.py
```

### Skip extraction (use existing intermediate files):

```bash
python scripts/run_pipeline.py --skip-extract
```

## Configuration

All parameters are configurable via `config/config.json`. Key parameters:

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

All input/output file paths are configurable in `config/config.json`. Paths are relative to the BASMA directory.

## Output Files

All output files are written to `data/output/`:

- **BASMA Easiness by Word.csv** - Complete easiness scores for all words with all computed features
- **BASMA IDs with E-M-H.csv** - One row per concept ID with the best Easy, Medium, and Hard word selected
- **BASMA IDs with All E-M-H (long).csv** - All words from all concepts, organized by category
- **BASMA IDs with All E-M-H (long, triplets only).csv** - All words from concepts that have all three categories (Easy, Medium, Hard)

## Customizing Parameters

To adjust the easiness scoring:

1. **Modify thresholds in config/config.json**:
   - Change `mapping_thresholds` to adjust L/M/H boundaries
   - Change `category_thresholds` to adjust Easy/Medium/Hard boundaries

2. **Update the scoring table**:
   - Modify `data/intermediate/BASMA Plan - Temp (1).csv` to change scores for specific factor combinations
   - Update `scoring_table` config if the CSV structure changes

3. **Run the pipeline**:
   ```bash
   python scripts/run_pipeline.py
   ```

## Requirements

- Python 3.7+
- pandas
- numpy
- openpyxl (for Excel file support)

Install dependencies:
```bash
pip install pandas numpy openpyxl
```

## Notes

- The pipeline is designed to be reproducible: all parameters are in `config/config.json`
- Intermediate files can be reused by using `--skip-extract`
- All scripts accept `--config` to specify a custom config file path
- Paths in config are relative to the BASMA directory
- Scripts automatically resolve paths relative to the BASMA root directory
