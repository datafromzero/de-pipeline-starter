"""Where the faults of the headline seed (2026) sit among 20 other seeds. Run it with: uv run python scripts/seed_check.py

The lessons quote what seed 2026 does: how many pages get a 429 or a 500, how many requests fail
before a page is served, and where the repeated record and the new column fall. Those are facts of
one seed, not of the API, so this script prints the same numbers for seeds 100 to 119.
"""

import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mock_api  # noqa: E402

PAGES = 33  # a full pull at 100 records a page, as the lessons run it


def faults(seed):
    """For one seed: pages with a 429, pages with a 500, and the failed requests of a full pull."""
    kinds = {429: 0, 500: 0}
    failed = 0
    for page in range(PAGES):
        first = mock_api.planned_fault(seed, page * 100, 0)
        if first is None:
            continue
        kinds[first] += 1
        failed += 1 + (mock_api.planned_fault(seed, page * 100, 1) is not None)
    return kinds[429], kinds[500], failed


def repeat_page(seed):
    """The page where the repeated record starts (page numbers count from 1)."""
    return mock_api.repeat_index(seed) // 100 + 2


if __name__ == "__main__":
    rows = {seed: faults(seed) for seed in [2026, *range(100, 120)]}
    print("seed  pages with 429  pages with 500  failed requests")
    for seed, (n429, n500, failed) in rows.items():
        print(f"{seed:>4}  {n429:>14}  {n500:>14}  {failed:>15}")
    others = [v for seed, v in rows.items() if seed != 2026]
    for name, index in (("pages with 429", 0), ("pages with 500", 1), ("failed requests", 2)):
        values = [v[index] for v in others]
        print(f"{name}: seed 2026 has {rows[2026][index]}; the 20 others have median {statistics.median(values)}, range {min(values)} to {max(values)}")
    pages = [repeat_page(seed) for seed in [2026, *range(100, 120)]]
    print(f"the repeated record starts page {pages[0]} for seed 2026; for the 20 others the pages run {min(pages[1:])} to {max(pages[1:])}")
    print(f"the new column starts on page 20 for every seed (it follows the date 2026-05-01, not the seed); {math.ceil(3288 / 100)} pages in all")
