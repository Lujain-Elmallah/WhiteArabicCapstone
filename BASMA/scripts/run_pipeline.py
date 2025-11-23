#!/usr/bin/env python3
"""
Main pipeline script to run the complete BASMA easiness computation workflow.

Usage:
    python run_pipeline.py [--config config.json]

The pipeline runs:
1. extract.py - Extract and compute features from MADAR lexicon
2. compute_easiness.py - Compute easiness scores
3. select_targets.py - Select best Easy/Medium/Hard words per concept
4. select_targets_all.py - Generate long-form files
"""

import sys
import subprocess
import json
from pathlib import Path
import argparse


def load_config(config_path: Path) -> dict:
    """Load configuration from JSON file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with config_path.open('r') as f:
        return json.load(f)


def run_script(script_name: str, config: dict, verbose: bool = True) -> bool:
    """Run a Python script and return success status."""
    # Scripts are in scripts/ directory, run from BASMA root
    scripts_dir = Path(__file__).parent
    script_path = scripts_dir / script_name
    basma_root = scripts_dir.parent  # BASMA directory
    
    if not script_path.exists():
        print(f"ERROR: Script not found: {script_path}")
        return False
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Running: {script_name}")
        print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=basma_root,  # Run from BASMA root so paths resolve correctly
            check=True,
            capture_output=not verbose,
            text=True
        )
        if verbose and result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {script_name} failed with exit code {e.returncode}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run the complete BASMA easiness computation pipeline"
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Path to configuration file (default: config.json)'
    )
    parser.add_argument(
        '--skip-extract',
        action='store_true',
        help='Skip the extract.py step (use existing intermediate files)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        default=True,
        help='Show detailed output (default: True)'
    )
    
    args = parser.parse_args()
    
    # Load config (default to config/config.json in BASMA directory)
    basma_root = Path(__file__).parent.parent
    if args.config == 'config.json':
        config_path = basma_root / 'config' / 'config.json'
    else:
        config_path = Path(args.config)
    try:
        config = load_config(config_path)
        print(f"Loaded configuration from: {config_path}")
    except Exception as e:
        print(f"ERROR: Failed to load config: {e}")
        return 1
    
    # Pipeline steps
    steps = []
    
    if not args.skip_extract:
        steps.append(('extract.py', 'Extract features from MADAR lexicon'))
    
    steps.extend([
        ('compute_easiness.py', 'Compute easiness scores'),
        ('select_targets.py', 'Select best Easy/Medium/Hard words'),
        ('select_targets_all.py', 'Generate long-form files')
    ])
    
    # Run pipeline
    print(f"\n{'='*60}")
    print("BASMA Easiness Computation Pipeline")
    print(f"{'='*60}")
    
    for i, (script, description) in enumerate(steps, 1):
        print(f"\n[{i}/{len(steps)}] {description}")
        if not run_script(script, config, args.verbose):
            print(f"\nPipeline failed at step {i}: {script}")
            return 1
    
    print(f"\n{'='*60}")
    print("Pipeline completed successfully!")
    print(f"{'='*60}")
    
    # Show output files
    output_files = config['files']['output']
    print("\nGenerated output files:")
    for key, filename in output_files.items():
        filepath = Path(__file__).parent / filename
        if filepath.exists():
            print(f"  ✓ {filename}")
        else:
            print(f"  ✗ {filename} (not found)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

