#!/usr/bin/env python3
"""Claim the next free PRD number in a repo, atomically.

    allocate_prd_number.py <repo> <slug>

Scans every `docs/dev/project-management/prds/` subdirectory plus `docs/dev/project-management/discovery/` for
`NNNNN-` prefixes, then creates an EMPTY file at the next free number and prints
its path. The caller writes the body into that file.

The create-prd convention is scan, write, then re-scan and renumber if someone
claimed your number in between. This claims with `O_CREAT | O_EXCL` instead, so
the file either did not exist and is now yours, or it existed and we move to the
next number. There is no window to lose, and no re-scan to forget.

Numbers are never reused: a parked or completed PRD keeps its number, which is
why the scan covers every lifecycle directory rather than just `backlog/`.
"""

from __future__ import annotations

import errno
import fcntl
import os
import re
import subprocess
import sys
from pathlib import Path

PREFIX_RE = re.compile(r"^(\d{5})-")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# A runaway loop would otherwise spin through five digits of nothing.
MAX_ATTEMPTS = 200


def claimed_numbers(repo: Path) -> set[int]:
    """Every sequence number already spoken for anywhere in the repo."""
    roots = [repo / "docs" / "dev" / "project-management" / "prds", repo / "docs" / "dev" / "project-management" / "discovery"]
    numbers: set[int] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.md"):
            match = PREFIX_RE.match(path.name)
            if match:
                numbers.add(int(match.group(1)))
    return numbers


def claim(repo: Path, slug: str) -> Path:
    """Create an empty PRD file at the next free number and return its path."""
    if not SLUG_RE.match(slug):
        raise SystemExit(f"slug must be kebab-case, got {slug!r}")

    backlog = repo / "docs" / "dev" / "project-management" / "prds" / "backlog"
    backlog.mkdir(parents=True, exist_ok=True)

    # Writers with different slugs never collide on a file name, so the
    # exclusive create alone cannot keep them off one number. Serialize the
    # scan-and-create on a lock held on the prds/ directory itself, which
    # leaves no lock file behind.
    lock_fd = os.open(backlog.parent, os.O_RDONLY)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        number = max(claimed_numbers(repo), default=0) + 1
        for _ in range(MAX_ATTEMPTS):
            target = backlog / f"{number:05d}-{slug}-v1.md"
            try:
                # Exclusive create still guards against a writer that does not
                # take the lock (a hand-made file, another tool).
                os.close(os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644))
                return target
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                number += 1
    finally:
        os.close(lock_fd)
    raise SystemExit(f"no free PRD number after {MAX_ATTEMPTS} attempts from {number}")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: allocate_prd_number.py <repo> <slug>", file=sys.stderr)
        return 2

    repo = Path(argv[1]).resolve()
    if not repo.is_dir():
        print(f"error: {repo} does not exist", file=sys.stderr)
        return 1

    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or Path(result.stdout.strip()).resolve() != repo:
        print(f"error: {repo} is not a git work-tree top level", file=sys.stderr)
        return 1

    print(claim(repo, argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
