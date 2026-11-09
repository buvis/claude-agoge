"""The numbering rule agoge's PRD emission depends on.

    uv run --with pytest pytest test_allocate_prd_number.py

Numbering is deterministic, so it lives in code rather than in a prompt: the
same repo must always yield the same next number, and two writers must never
walk away believing they own the same one.
"""

from __future__ import annotations

import multiprocessing
import os
import subprocess
import sys
from pathlib import Path

import pytest
from allocate_prd_number import claim, claimed_numbers

SCRIPT = Path(__file__).resolve().parent / "allocate_prd_number.py"


def seed(repo: Path, relative: str) -> Path:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# stub\n", encoding="utf-8")
    return path


def test_first_number_in_an_empty_repo_is_one(tmp_path: Path) -> None:
    assert claim(tmp_path, "first-thing").name == "00001-first-thing-v1.md"


def test_scan_covers_every_lifecycle_directory_and_discovery(tmp_path: Path) -> None:
    """A parked PRD keeps its number, so hold/ must count as claimed."""
    seed(tmp_path, "docs/dev/project-management/prds/backlog/00003-a-v1.md")
    seed(tmp_path, "docs/dev/project-management/prds/wip/00007-b-v1.md")
    seed(tmp_path, "docs/dev/project-management/prds/done/00011-c-v1.md")
    seed(tmp_path, "docs/dev/project-management/prds/hold/00042-d-v1.md")
    seed(tmp_path, "docs/dev/project-management/discovery/00099-e.md")
    assert claimed_numbers(tmp_path) == {3, 7, 11, 42, 99}
    assert claim(tmp_path, "next-one").name == "00100-next-one-v1.md"


def test_a_taken_filename_pushes_the_claim_to_the_next_number(tmp_path: Path) -> None:
    """The exclusive create is the guard; this is it firing."""
    seed(tmp_path, "docs/dev/project-management/prds/backlog/00005-taken-v1.md")
    # Same slug, so the scan's max+1 lands on a name that already exists.
    seed(tmp_path, "docs/dev/project-management/prds/backlog/00006-collide-v1.md")
    assert claim(tmp_path, "collide").name == "00007-collide-v1.md"


def test_two_claims_never_share_a_number(tmp_path: Path) -> None:
    first = claim(tmp_path, "one")
    second = claim(tmp_path, "two")
    assert first != second
    assert first.name == "00001-one-v1.md"
    assert second.name == "00002-two-v1.md"


def test_the_claimed_file_exists_and_is_empty(tmp_path: Path) -> None:
    """The caller writes the body; the claim only reserves the name."""
    claimed = claim(tmp_path, "reserved")
    assert claimed.is_file()
    assert claimed.read_text(encoding="utf-8") == ""


def test_non_prd_filenames_are_ignored(tmp_path: Path) -> None:
    seed(tmp_path, "docs/dev/project-management/prds/backlog/README.md")
    seed(tmp_path, "docs/dev/project-management/prds/backlog/FASTTRACK-PLAN-v5.md")
    seed(tmp_path, "docs/dev/project-management/prds/backlog/0042-too-short-v1.md")
    assert claimed_numbers(tmp_path) == set()


@pytest.mark.parametrize(
    "slug", ["Not Kebab", "trailing-", "UPPER", "under_score", "", "ab\n"]
)
def test_a_bad_slug_is_refused_rather_than_normalized(
    tmp_path: Path, slug: str
) -> None:
    """Guessing what the caller meant would put a wrong name in the backlog."""
    with pytest.raises(SystemExit):
        claim(tmp_path, slug)


PARALLEL_WRITERS = 16


def claim_after_barrier(repo: str, slug: str, barrier, results) -> None:
    """One writer: line up with the others, then claim at the same instant."""
    try:
        barrier.wait(timeout=30)
        results.put((slug, str(claim(Path(repo), slug))))
    except BaseException as exc:  # surface every failure to the parent
        results.put((slug, f"ERROR: {exc!r}"))


def test_parallel_distinct_slugs_get_distinct_numbers(tmp_path: Path) -> None:
    """Writers with different slugs never share a file name, so the exclusive
    create alone cannot keep them off one number."""
    context = multiprocessing.get_context("fork")
    barrier = context.Barrier(PARALLEL_WRITERS)
    results = context.Queue()
    slugs = [f"writer-{index}" for index in range(PARALLEL_WRITERS)]
    workers = [
        context.Process(
            target=claim_after_barrier, args=(str(tmp_path), slug, barrier, results)
        )
        for slug in slugs
    ]
    for worker in workers:
        worker.start()
    claimed = dict(results.get(timeout=60) for _ in workers)
    for worker in workers:
        worker.join(timeout=60)
        assert worker.exitcode == 0

    assert not [value for value in claimed.values() if value.startswith("ERROR")]
    assert sorted(claimed) == sorted(slugs)
    paths = {slug: Path(value) for slug, value in claimed.items()}
    numbers = []
    for slug, path in paths.items():
        assert path.is_file()
        assert path.name[6:] == f"{slug}-v1.md"
        numbers.append(int(path.name[:5]))
    assert sorted(numbers) == list(range(1, PARALLEL_WRITERS + 1))

    prds = tmp_path / "docs" / "dev" / "project-management" / "prds"
    on_disk = {path for path in prds.rglob("*") if not path.is_dir()}
    assert on_disk == set(paths.values())


def test_cli_prints_the_path_it_claimed(tmp_path: Path) -> None:
    subprocess.run(
        ["git", "init", str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path), "from-the-cli"],
        capture_output=True,
        text=True,
        check=True,
    )
    claimed = Path(result.stdout.strip())
    assert claimed.is_file()
    assert claimed.name == "00001-from-the-cli-v1.md"


def test_cli_refuses_wrong_argument_counts(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "usage:" in result.stderr


def test_cli_refuses_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(missing), "a-slug"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert (
        result.stderr
        == f"allocate_prd_number: {missing.resolve()} is not the top level of a git work tree\n"
    )
    assert not missing.exists()


def test_cli_refuses_non_repo_dir(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path), "a-slug"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert (
        result.stderr
        == f"allocate_prd_number: {tmp_path.resolve()} is not the top level of a git work tree\n"
    )
    assert not (tmp_path / "docs").exists()


def test_cli_refuses_repo_subdirectory(tmp_path: Path) -> None:
    subprocess.run(
        ["git", "init", str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    subdir = tmp_path / "nested"
    subdir.mkdir()
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(subdir), "a-slug"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert (
        result.stderr
        == f"allocate_prd_number: {subdir.resolve()} is not the top level of a git work tree\n"
    )
    assert not (subdir / "docs").exists()


def test_cli_refuses_prds_symlink_leaving_repo(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """A `prds` symlink pointing outside the repo must not be followed into a write."""
    subprocess.run(
        ["git", "init", str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    outside = tmp_path_factory.mktemp("outside-prds")
    (tmp_path / "docs" / "dev" / "project-management").mkdir(parents=True)
    (tmp_path / "docs" / "dev" / "project-management" / "prds").symlink_to(
        outside, target_is_directory=True
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path), "escaping-slug"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert list(outside.rglob("*")) == []


def test_cli_refuses_backlog_symlink_leaving_repo(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """A `backlog` symlink pointing outside the repo must not be followed into a write."""
    subprocess.run(
        ["git", "init", str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    outside = tmp_path_factory.mktemp("outside-backlog")
    (tmp_path / "docs" / "dev" / "project-management" / "prds").mkdir(parents=True)
    (tmp_path / "docs" / "dev" / "project-management" / "prds" / "backlog").symlink_to(
        outside, target_is_directory=True
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path), "escaping-slug"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert list(outside.rglob("*")) == []


def test_cli_follows_symlink_inside_repo(tmp_path: Path) -> None:
    """A symlink that stays inside the repo (e.g. a shared prds dir) is not a traversal and must still work."""
    subprocess.run(
        ["git", "init", str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    real_backlog_parent = tmp_path / "shared" / "prds"
    real_backlog_parent.mkdir(parents=True)
    (tmp_path / "docs" / "dev" / "project-management").mkdir(parents=True)
    (tmp_path / "docs" / "dev" / "project-management" / "prds").symlink_to(
        real_backlog_parent, target_is_directory=True
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path), "inside-slug"],
        capture_output=True,
        text=True,
        check=True,
    )
    claimed = Path(result.stdout.strip())
    assert claimed.is_file()
    assert claimed.name == "00001-inside-slug-v1.md"
    assert (
        claimed.resolve()
        == (real_backlog_parent / "backlog" / "00001-inside-slug-v1.md").resolve()
    )


def test_cli_ignores_inherited_git_dir_from_unrelated_repo(tmp_path: Path) -> None:
    """An inherited GIT_DIR must not let the check pass for a plain directory."""
    decoy = tmp_path / "decoy-repo"
    decoy.mkdir()
    subprocess.run(
        ["git", "init", str(decoy)],
        capture_output=True,
        text=True,
        check=True,
    )
    plain = tmp_path / "plain-dir"
    plain.mkdir()
    env = {**os.environ, "GIT_DIR": str(decoy / ".git")}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(plain), "a-slug"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 2
    assert (
        result.stderr
        == f"allocate_prd_number: {plain.resolve()} is not the top level of a git work tree\n"
    )
    assert not (plain / "docs").exists()
