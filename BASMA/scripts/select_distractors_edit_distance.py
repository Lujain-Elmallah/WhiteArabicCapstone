#!/usr/bin/env python3
"""
Generate distractors based on edit distance from medium and hard words only.

For each concept in the random select file:
- For each target (easy/medium/hard), compute edit distance to medium and hard 
  words from all_words.csv (excluding same concept)
- Pick 2 distractors per target: start with lowest edit distance, if multiple 
  candidates at same distance pick 2 randomly, if only 1 pick it and move to 
  next rank until we have 2 distractors

Output: 6 distractor columns (2 for easy, 2 for medium, 2 for hard targets)
"""

import csv
import random
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
RANDOM_SELECT_CSV = ROOT / "data" / "output" / "BASMA Plan - Random Select.csv"
ALL_WORDS_CSV = ROOT / "data" / "output" / "BASMA Plan - all_words.csv"
CONCEPTS_GROUPED_CSV = ROOT / "data" / "output" / "BASMA Plan - Concepts Grouped.csv"
OUTPUT_CSV = ROOT / "data" / "output" / "BASMA Plan - Random Select with Edit Distance Distractors.csv"

# Use a fixed seed for reproducibility
random.seed(42)


def edit_distance(a: str, b: str) -> int:
    """Compute Levenshtein distance (iterative DP)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    # Ensure a is the shorter string
    if len(a) > len(b):
        a, b = b, a

    prev = list(range(len(a) + 1))
    for j, bj in enumerate(b, start=1):
        curr = [j]
        for i, ai in enumerate(a, start=1):
            cost = 0 if ai == bj else 1
            curr.append(
                min(
                    prev[i] + 1,      # deletion
                    curr[i - 1] + 1,  # insertion
                    prev[i - 1] + cost,  # substitution
                )
            )
        prev = curr
    return prev[-1]


def strip_whitespace(s: str) -> str:
    """Strip whitespace from string."""
    return s.strip() if s else ""


def load_concept_words() -> Dict[int, Dict[str, List[str]]]:
    """
    Load ALL easy/medium/hard words for each concept from Concepts Grouped.
    Returns: dict mapping concept ID to dict with 'easy', 'medium', 'hard' lists
    """
    concept_words = {}
    
    with CONCEPTS_GROUPED_CSV.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get('ID', '').strip()
            if not cid:
                continue
            try:
                concept_id = int(cid)
            except ValueError:
                continue
            
            # Get all easy words
            easy_words = []
            easy = row.get('Easy', '').strip()
            if easy:
                easy_words = [w.strip() for w in easy.split('|') if w.strip()]
            
            # Get all medium words
            medium_words = []
            medium = row.get('Medium', '').strip()
            if medium:
                medium_words = [w.strip() for w in medium.split('|') if w.strip()]
            
            # Get all hard words
            hard_words = []
            hard = row.get('Hard', '').strip()
            if hard:
                hard_words = [w.strip() for w in hard.split('|') if w.strip()]
            
            concept_words[concept_id] = {
                'easy': easy_words,
                'medium': medium_words,
                'hard': hard_words
            }
    
    return concept_words


def load_all_words() -> Dict[int, List[Tuple[str, str, str]]]:
    """
    Load ALL medium and hard words from all_words.csv.
    
    This includes ALL concepts from the full dataset, not just those in the 
    random select file. Includes medium/hard words even if the concept doesn't 
    have all three difficulty levels.
    
    Returns: dict mapping concept ID to list of (CODA, EasinessCategory, POS) tuples
    Only includes Medium and Hard words.
    """
    candidates = defaultdict(list)
    
    with ALL_WORDS_CSV.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            coda = strip_whitespace(row.get('CODA', ''))
            if not coda:
                continue
            
            cid = row.get('ID', '').strip()
            if not cid:
                continue
            try:
                concept_id = int(cid)
            except ValueError:
                continue
            
            category = row.get('EasinessCategory', '').strip()
            pos = row.get('POS', '').strip()
            # Only include Medium and Hard words from ALL concepts
            # (not filtered by whether concept is in random select file)
            if category in ('Medium', 'Hard'):
                candidates[concept_id].append((coda, category, pos))
    
    return dict(candidates)


def select_distractors_by_edit_distance(
    target_words: List[str],
    target_pos: str,
    exclude_concept_id: int,
    all_candidates: Dict[int, List[Tuple[str, str, str]]],
    exclude_words: List[str],
    already_selected: List[str],
    k: int = 2
) -> List[str]:
    """
    Select k distractors based on edit distance.
    
    - Compute edit distance from each target_word to all medium/hard words
    - Use minimum distance across all target words
    - Only include candidates with the same POS as target
    - Exclude words from the same concept (all easy/medium/hard words from that concept)
    - Exclude words already selected as distractors for this concept
    - Group by edit distance
    - Pick k distractors: start with lowest distance, if multiple at same 
      distance pick randomly, if only 1 pick it and move to next rank
    """
    if not target_words:
        return []
    
    # Strip and filter target words
    target_words = [strip_whitespace(w) for w in target_words if strip_whitespace(w)]
    if not target_words:
        return []
    
    target_pos = strip_whitespace(target_pos)
    if not target_pos:
        return []
    
    # Create set of excluded words for fast lookup
    exclude_set = set(w.strip().lower() if w else "" for w in exclude_words)
    for tw in target_words:
        exclude_set.add(tw.lower())
    
    # Also exclude words already selected as distractors
    already_selected_set = set(w.strip().lower() if w else "" for w in already_selected)
    exclude_set.update(already_selected_set)
    
    # Compute edit distances to all candidates
    # For each candidate, use minimum distance to any target word
    distances = []
    for concept_id, words in all_candidates.items():
        if concept_id == exclude_concept_id:
            continue  # Exclude same concept
        
        for coda, _, pos in words:
            coda = strip_whitespace(coda)
            if not coda:
                continue
            
            # Only include candidates with the same POS
            if strip_whitespace(pos) != target_pos:
                continue
            
            # Exclude all words from the target concept (easy/medium/hard)
            if coda.lower() in exclude_set:
                continue
            
            # Compute minimum distance to any target word
            min_dist = min(edit_distance(tw, coda) for tw in target_words)
            distances.append((min_dist, coda))
    
    if not distances:
        return []
    
    # Group by edit distance
    by_distance = defaultdict(list)
    for dist, word in distances:
        by_distance[dist].append(word)
    
    # Sort distances
    sorted_distances = sorted(by_distance.keys())
    
    # Pick k distractors
    picks = []
    for dist in sorted_distances:
        candidates_at_dist = by_distance[dist]
        # Remove duplicates while preserving order
        unique_candidates = []
        seen = set()
        for c in candidates_at_dist:
            if c not in seen:
                unique_candidates.append(c)
                seen.add(c)
        
        needed = k - len(picks)
        if needed <= 0:
            break
        
        if len(unique_candidates) >= needed:
            # Pick randomly from candidates at this distance
            random.shuffle(unique_candidates)
            picks.extend(unique_candidates[:needed])
        else:
            # Take all candidates at this distance and continue to next rank
            picks.extend(unique_candidates)
    
    return picks[:k]


def main():
    """Main function to generate distractors."""
    # Load all medium and hard words
    print("Loading candidates from all_words.csv...")
    all_candidates = load_all_words()
    print(f"Loaded {sum(len(words) for words in all_candidates.values())} medium/hard words from {len(all_candidates)} concepts")
    
    # Load all words for each concept (to exclude all easy/medium/hard from target concept)
    print("Loading concept words from Concepts Grouped...")
    concept_words = load_concept_words()
    print(f"Loaded words for {len(concept_words)} concepts")
    
    # Load random select concepts
    print("Loading target concepts...")
    target_concepts = []
    with RANDOM_SELECT_CSV.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            target_concepts.append(row)
    
    print(f"Processing {len(target_concepts)} concepts...")
    
    # Process each concept
    output_rows = []
    for row in target_concepts:
        concept_id = row.get('ID', '').strip()
        try:
            cid = int(concept_id)
        except ValueError:
            print(f"Warning: Invalid ID '{concept_id}', skipping")
            continue
        
        # Get all words from this concept by level
        concept_data = concept_words.get(cid, {'easy': [], 'medium': [], 'hard': []})
        all_easy_words = concept_data.get('easy', [])
        all_medium_words = concept_data.get('medium', [])
        all_hard_words = concept_data.get('hard', [])
        
        # Get all words from this concept to exclude (all easy/medium/hard)
        exclude_words = all_easy_words + all_medium_words + all_hard_words
        
        # Get the selected targets for display (from random select file)
        easy_target = strip_whitespace(row.get('Easy_target', ''))
        medium_target = strip_whitespace(row.get('Medium_target', ''))
        hard_target = strip_whitespace(row.get('Hard_target', ''))
        
        # Get MSA for this concept (to include in easy distractor comparison)
        msa = strip_whitespace(row.get('MSA', ''))
        # MSA might have multiple words separated by "،" - split and clean
        msa_words = []
        if msa:
            # Split by Arabic comma and clean
            for msa_part in msa.split('،'):
                msa_clean = strip_whitespace(msa_part)
                if msa_clean:
                    msa_words.append(msa_clean)
        
        # Get POS for this concept
        target_pos = strip_whitespace(row.get('POS', ''))
        
        # For easy distractors: include MSA words as additional targets for edit distance
        # For medium/hard: use only dialectal words
        easy_target_words = all_easy_words + msa_words
        
        # Select 2 distractors for each level using ALL words from that level
        # Only candidates with the same POS will be considered
        # Easy distractors also compare against MSA
        # Track already selected distractors to ensure uniqueness across all 6
        already_selected = []
        
        easy_distractors = select_distractors_by_edit_distance(
            easy_target_words, target_pos, cid, all_candidates, exclude_words, already_selected, k=2
        )
        already_selected.extend(easy_distractors)
        
        medium_distractors = select_distractors_by_edit_distance(
            all_medium_words, target_pos, cid, all_candidates, exclude_words, already_selected, k=2
        )
        already_selected.extend(medium_distractors)
        
        hard_distractors = select_distractors_by_edit_distance(
            all_hard_words, target_pos, cid, all_candidates, exclude_words, already_selected, k=2
        )
        
        # Create output row
        output_row = {
            'ID': row.get('ID', ''),
            'English': row.get('English', ''),
            'French': row.get('French', ''),
            'MSA': row.get('MSA', ''),
            'POS': row.get('POS', ''),
            'Easy_target': easy_target,
            'Medium_target': medium_target,
            'Hard_target': hard_target,
            'Easy_distractor_1': easy_distractors[0] if len(easy_distractors) > 0 else '',
            'Easy_distractor_2': easy_distractors[1] if len(easy_distractors) > 1 else '',
            'Medium_distractor_1': medium_distractors[0] if len(medium_distractors) > 0 else '',
            'Medium_distractor_2': medium_distractors[1] if len(medium_distractors) > 1 else '',
            'Hard_distractor_1': hard_distractors[0] if len(hard_distractors) > 0 else '',
            'Hard_distractor_2': hard_distractors[1] if len(hard_distractors) > 1 else '',
        }
        output_rows.append(output_row)
    
    # Write output
    print(f"Writing output to {OUTPUT_CSV}...")
    fieldnames = [
        'ID', 'English', 'French', 'MSA', 'POS',
        'Easy_target', 'Medium_target', 'Hard_target',
        'Easy_distractor_1', 'Easy_distractor_2',
        'Medium_distractor_1', 'Medium_distractor_2',
        'Hard_distractor_1', 'Hard_distractor_2'
    ]
    
    with OUTPUT_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)
    
    print(f"Wrote {len(output_rows)} rows to {OUTPUT_CSV}")


if __name__ == '__main__':
    main()

