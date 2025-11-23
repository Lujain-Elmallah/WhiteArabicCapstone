# Config File Guide

## How the Config File Works

The `config.json` file is a JSON configuration file that stores all the parameters your scripts need. Instead of hardcoding values in Python, everything is in one place so you can easily tune parameters without editing code.

## Structure Overview

```json
{
  "files": { ... },              // File paths
  "mapping_thresholds": { ... }, // How to convert numbers to L/M/H
  "category_thresholds": { ... }, // How to convert scores to Easy/Medium/Hard
  "scoring_table": { ... },      // How to read the scoring CSV
  "frequencies_file": { ... }    // Column positions in frequencies file
}
```

## How Scripts Use It

### 1. Loading the Config

```python
# Script loads the JSON file
config = load_config(Path("config/config.json"))

# Now you can access values like:
files = config['files']
thresholds = config['mapping_thresholds']
```

### 2. Using File Paths

```python
# Instead of hardcoding:
# scores_csv = Path("BASMA Plan - Scores.csv")

# Script reads from config:
files = config['files']
scores_csv = root / files['intermediate']['scores']
# Result: "data/intermediate/BASMA Plan - Scores.csv"
```

### 3. Using Mapping Thresholds

**What it does:** Converts raw numbers (like `DFreq = 3`) into levels (`L`, `M`, or `H`)

**Example - DFreq mapping:**
```python
# In compute_easiness.py:
def map_dfreq(dfreq_raw: str, config: dict) -> str:
    thresholds = config['mapping_thresholds']['dfreq']
    rl = int(dfreq_raw)  # e.g., rl = 3
    
    if rl <= thresholds['low_max']:      # 3 <= 1? No
        return 'L'
    if rl <= thresholds['medium_max']:   # 3 <= 4? Yes!
        return 'M'
    return 'H'
```

**What the config says:**
- `low_max: 1` → Values 0-1 become `L`
- `medium_max: 4` → Values 2-4 become `M`
- Values 5+ become `H`

**To change it:** Edit the numbers in config.json:
```json
"dfreq": {
  "low_max": 2,      // Change from 1 to 2
  "medium_max": 5    // Change from 4 to 5
}
```

### 4. Using Category Thresholds

**What it does:** Converts easiness scores into Easy/Medium/Hard categories

**Example:**
```python
# If a word has EasinessScore = 1200
score = 1200
if score >= config['category_thresholds']['easy_min']:  # 1200 >= 1000? Yes!
    category = 'Easy'
elif score >= config['category_thresholds']['medium_min']:  # 1200 >= 100? Yes, but already Easy
    category = 'Medium'
else:
    category = 'Hard'
```

**What the config says:**
- `easy_min: 1000` → Scores >= 1000 = Easy
- `medium_min: 100` → Scores >= 100 = Medium
- Scores < 100 = Hard

**To change it:** Edit the thresholds:
```json
"category_thresholds": {
  "easy_min": 1500,    // Make Easy category harder to achieve
  "medium_min": 200    // Make Medium category harder to achieve
}
```

### 5. Using Scoring Table Config

**What it does:** Tells the script how to read the scoring CSV file

**The scoring CSV looks like:**
```
Row 13: ASim, FSim, DFreq, DCom, RCom, Easiness Score, ...
Row 14: S,    S,    H,     H,    H,    1400,          ...
```

**The config tells the script:**
- `header_row: 13` → Headers are on row 13 (1-indexed, so index 12 in code)
- `data_start_row: 14` → Data starts on row 14 (1-indexed, so index 13 in code)
- `columns.asim: 3` → ASim is in column 3 (0-indexed)
- `columns.score: 8` → Score is in column 8 (0-indexed)

**In code:**
```python
# Script reads row 14 (index 13):
row = rows[13]
asim = row[3]    # Column 3 = ASim
score = row[8]   # Column 8 = Score
```

**To change it:** If your CSV structure changes, update these numbers:
```json
"scoring_table": {
  "header_row": 15,    // If headers moved to row 15
  "data_start_row": 16, // If data starts at row 16
  "columns": {
    "asim": 4,         // If ASim moved to column 4
    ...
  }
}
```

### 6. Using Frequencies File Config

**What it does:** Tells the script which columns contain which data in the frequencies CSV

**The frequencies CSV has columns:**
```
English (col 0), French (col 1), MSA (col 2), POS (col 3), ..., CODA (col 6), ..., RCom (col 13)
```

**The config maps:**
```json
"frequencies_file": {
  "columns": {
    "english": 0,   // English is column 0
    "coda": 6,      // CODA is column 6
    "rcom": 13      // RCom is column 13
  }
}
```

**In code:**
```python
cols = config['frequencies_file']['columns']
english = row[cols['english']]  # row[0]
coda = row[cols['coda']]        # row[6]
rcom = row[cols['rcom']]        # row[13]
```

## Real Example: Changing Thresholds

**Scenario:** You want to make it easier for words to be categorized as "Easy"

**Before:**
```json
"category_thresholds": {
  "easy_min": 1000,
  "medium_min": 100
}
```

**After:**
```json
"category_thresholds": {
  "easy_min": 800,    // Lowered from 1000
  "medium_min": 50    // Lowered from 100
}
```

**Result:** More words will be categorized as Easy and Medium.

## Why This is Better

**Without config (hardcoded):**
```python
# In compute_easiness.py:
if rl <= 1:
    return 'L'
if rl <= 4:
    return 'M'
return 'H'
```
- To change thresholds, you edit Python code
- Hard to remember what values mean
- Risk of breaking code

**With config:**
```python
# In compute_easiness.py:
thresholds = config['mapping_thresholds']['dfreq']
if rl <= thresholds['low_max']:
    return 'L'
```
- Change values in JSON (no code editing)
- Self-documenting with descriptions
- All parameters in one place

## Quick Reference

| Config Section | What It Controls | Example Value |
|---------------|-----------------|---------------|
| `files.input.*` | Input file paths | `"data/input/roots.tsv"` |
| `files.output.*` | Output file paths | `"data/output/easiness.csv"` |
| `mapping_thresholds.dfreq` | DFreq → L/M/H conversion | `low_max: 1, medium_max: 4` |
| `mapping_thresholds.dcom` | DCom → L/M/H conversion | `low_max: 1, medium_max: 3` |
| `mapping_thresholds.rcom` | RCom → L/M/H conversion | `low_max: 1, medium_max: 3` |
| `category_thresholds` | Score → Easy/Medium/Hard | `easy_min: 1000, medium_min: 100` |
| `scoring_table.columns` | Which CSV columns to read | `asim: 3, score: 8` |

## Common Tasks

### Change where Easy/Medium/Hard boundaries are:
Edit `category_thresholds.easy_min` and `category_thresholds.medium_min`

### Change how DFreq maps to L/M/H:
Edit `mapping_thresholds.dfreq.low_max` and `medium_max`

### Change file locations:
Edit paths in `files.input.*`, `files.intermediate.*`, or `files.output.*`

### Change how scoring CSV is read:
Edit `scoring_table.header_row`, `data_start_row`, or `columns.*`

