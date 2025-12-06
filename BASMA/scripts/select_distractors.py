#!/usr/bin/env python3
"""
Generate three dialectal distractors per concept for the random-select list.

Heuristic (no embeddings):
- Pull candidate dialectal words from other concepts (same POS) in
  `BASMA Plan - Concepts Grouped.csv`.
- Score candidates by minimum normalized edit distance to any dialectal word
  in the target concept; closer strings are preferred.
- Keep the top 6 scored candidates, then randomly pick 3 (seeded for
  reproducibility). If not enough, backfill with random "Hard" words from
  other concepts with the same POS; if still short, fill from any remaining
  candidates.

Outputs: writes `BASMA Plan - Random Select with Distractors.csv`
with Easy_distractor / Medium_distractor / Hard_distractor columns filled.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
GROUPED_CSV = ROOT / "data" / "output" / "BASMA Plan - Concepts Grouped.csv"
RANDOM_SELECT_CSV = ROOT / "data" / "output" / "BASMA Plan - Random Select.csv"
OUTPUT_CSV = ROOT / "data" / "output" / "BASMA Plan - Random Select with Distractors.csv"

# Use a fixed seed for reproducibility
random.seed(42)


def split_words(raw: str) -> List[str]:
    """Split the pipe-separated dialectal word string into a list."""
    if not raw:
        return []
    # Split on pipe, trim whitespace, drop empties
    return [w.strip() for w in raw.split("|") if w.strip()]


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


def normalized_distance(a: str, b: str) -> float:
    """Normalized Levenshtein distance in [0, 1]."""
    if not a and not b:
        return 0.0
    dist = edit_distance(a, b)
    denom = max(len(a), len(b), 1)
    return dist / denom


def load_grouped() -> Dict[str, dict]:
    """Load grouped concepts into a dict keyed by ID."""
    concepts: Dict[str, dict] = {}
    with GROUPED_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get("ID", "").strip()
            if not cid:
                continue
            pos = row.get("POS", "").strip()
            easy = split_words(row.get("Easy", ""))
            med = split_words(row.get("Medium", ""))
            hard = split_words(row.get("Hard", ""))
            words = easy + med + hard
            concepts[cid] = {
                "pos": pos,
                "easy": easy,
                "medium": med,
                "hard": hard,
                "all_words": words,
            }
    return concepts


def build_candidates(concepts: Dict[str, dict]) -> List[Tuple[str, str, str, str]]:
    """
    Build a list of (word, pos, cid, level) for all concepts.
    level in {"easy", "medium", "hard"} based on source bucket.
    """
    pool = []
    for cid, data in concepts.items():
        pos = data["pos"]
        for w in data["easy"]:
            pool.append((w, pos, cid, "easy"))
        for w in data["medium"]:
            pool.append((w, pos, cid, "medium"))
        for w in data["hard"]:
            pool.append((w, pos, cid, "hard"))
    return pool


def select_distractors(
    anchors: List[str],
    pos: str,
    cid: str,
    candidates: List[Tuple[str, str, str, str]],
) -> List[str]:
    """
    Select exactly three distractors (easy/medium/hard slots) using three pools:
    - Easy slot: random from easy/medium words (same POS, other concepts) -> [rand]
    - Medium slot: random from hard words (same POS, other concepts) -> [hard]
    - Hard slot: random from top 6 closest (edit distance <= 2) same POS, other concepts -> [edit]
    Falls back to other pools if a primary pool is empty.
    """
    # Partition pools (same POS, other concepts, not anchors)
    easy_med_pool = [
        w for (w, c_pos, c_cid, lvl) in candidates
        if c_pos == pos and c_cid != cid and w not in anchors and lvl in {"easy", "medium"}
    ]

    hard_pool = [
        w for (w, c_pos, c_cid, lvl) in candidates
        if c_pos == pos and c_cid != cid and w not in anchors and lvl == "hard"
    ]

    edit_pool = [
        w for (w, c_pos, c_cid, _) in candidates
        if c_pos == pos and c_cid != cid and w not in anchors
    ]

    picks: List[str] = []

    # Easy slot
    random.shuffle(easy_med_pool)
    easy_pick = easy_med_pool[0] if easy_med_pool else ""
    if easy_pick:
        picks.append(f"{easy_pick} [rand]")

    # Medium slot
    random.shuffle(hard_pool)
    med_pick = hard_pool[0] if hard_pool else ""
    if med_pick:
        picks.append(f"{med_pick} [hard]")

    # Hard slot via edit distance (<=2), pick randomly from top 6
    if edit_pool:
        scored = []
        for w in edit_pool:
            score = min(normalized_distance(w, a) for a in anchors) if anchors else 1.0
            scored.append((score, w))
        scored = [sw for sw in scored if sw[0] <= 2 / max(len(sw[1]), 1)]  # normalized <= 2 chars
        scored.sort(key=lambda x: x[0])
        top_edit = [w for _, w in scored[:6]] if scored else []
        random.shuffle(top_edit)
        hard_pick = top_edit[0] if top_edit else ""
    else:
        hard_pick = ""

    if hard_pick:
        picks.append(f"{hard_pick} [edit]")

    # Fallbacks to ensure three outputs
    pools_for_fallback = [
        easy_med_pool,
        hard_pool,
        edit_pool,
    ]
    flat_fallback = []
    for pool in pools_for_fallback:
        flat_fallback.extend(pool)
    random.shuffle(flat_fallback)

    existing_words = {p.split(" [")[0] for p in picks}
    for w in flat_fallback:
        if len(picks) >= 3:
            break
        if w in existing_words or w in anchors:
            continue
        picks.append(f"{w} [rand]")
        existing_words.add(w)

    # Pad with empty strings if still short
    while len(picks) < 3:
        picks.append("")

    return picks[:3]


def main() -> None:
    if not GROUPED_CSV.exists():
        raise SystemExit(f"Grouped file not found: {GROUPED_CSV}")
    if not RANDOM_SELECT_CSV.exists():
        raise SystemExit(f"Random-select file not found: {RANDOM_SELECT_CSV}")

    concepts = load_grouped()
    candidates = build_candidates(concepts)

    # Hard-only pool for fallback
    hard_candidates = []
    for cid, data in concepts.items():
        pos = data["pos"]
        for w in data["hard"]:
            hard_candidates.append((w, pos, cid))

    with RANDOM_SELECT_CSV.open("r", encoding="utf-8") as f_in, OUTPUT_CSV.open(
        "w", newline="", encoding="utf-8"
    ) as f_out:
        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames or []
        out_fieldnames = fieldnames.copy()
        # Ensure distractor columns exist in output
        for col in ["Easy_distractor", "Medium_distractor", "Hard_distractor"]:
            if col not in out_fieldnames:
                out_fieldnames.append(col)

        writer = csv.DictWriter(f_out, fieldnames=out_fieldnames)
        writer.writeheader()

        for row in reader:
            cid = row.get("ID", "").strip()
            concept = concepts.get(cid)
            if not concept:
                # No concept info; write through
                writer.writerow(row)
                continue

            pos = concept["pos"]
            anchors = concept["all_words"]
            picks = select_distractors(
                anchors=anchors,
                pos=pos,
                cid=cid,
                candidates=candidates,
            )

            # Fill the three distractor slots
            row["Easy_distractor"] = picks[0] if len(picks) > 0 else ""
            row["Medium_distractor"] = picks[1] if len(picks) > 1 else ""
            row["Hard_distractor"] = picks[2] if len(picks) > 2 else ""

            writer.writerow(row)

    print(f"Wrote: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()

