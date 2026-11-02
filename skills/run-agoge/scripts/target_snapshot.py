#!/usr/bin/env python3
"""Snapshot a target repo's git state, then report what changed since.

    target_snapshot.py snapshot <repo> <out.json>
    target_snapshot.py compare <repo> <before.json> [--allow <path>]...

`snapshot` records HEAD, refs, local config, worktrees, the index, dirty
tracked paths and untracked paths into <out.json>, which must lie outside
<repo>. `compare` takes a fresh snapshot and prints a JSON report of
violations (head, ref, config, worktrees, index, tracked, untracked-removed)
plus newly `touched` untracked paths. `--allow` exempts a repo-relative path
from tracked, untracked-removed and touched only.

Exit 0 when unchanged, 1 when changed, 2 when the check cannot run (one
`target_snapshot: <reason>` line on stderr, no JSON). Any other unexpected
error also exits 2. Every git call runs with
`--no-optional-locks` and nothing is ever written inside <repo>.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys

VERSION = 1


class Fail(Exception):
    """The check cannot run; exits 2 with a one-line reason."""


def _git(repo: str, *args: str, allow_fail: bool = False) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(repo), *args],
        capture_output=True,
    )
    if result.returncode != 0 and not allow_fail:
        reason = result.stderr.decode(errors="replace").strip().splitlines()
        detail = reason[0] if reason else f"exit {result.returncode}"
        raise Fail(f"git {args[0]} failed: {detail}")
    return result


def _text(result: subprocess.CompletedProcess) -> str:
    return os.fsdecode(result.stdout).rstrip("\n")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _external_symlink_ancestor(repo: str, path: str) -> bool:
    """True when a directory component of `path` is a symlink escaping `repo`."""
    check = repo
    for part in os.path.dirname(path).split(os.sep):
        if not part:
            continue
        check = os.path.join(check, part)
        if os.path.islink(check):
            real = os.path.realpath(check)
            if os.path.commonpath([real, repo]) != repo:
                return True
    return False


def _fingerprint(repo: str, path: str) -> str:
    if _external_symlink_ancestor(repo, path):
        return "external-symlink"
    full = os.path.join(repo, path)
    if os.path.islink(full):
        return "link:" + _sha(os.fsencode(os.readlink(full)))
    if not os.path.exists(full):
        return "absent"
    if os.path.isdir(full):
        return "dir"
    with open(full, "rb") as handle:
        return _sha(handle.read())


def _resolve_repo(repo_arg: str) -> str:
    real = os.path.realpath(repo_arg)
    top = os.path.realpath(_text(_git(repo_arg, "rev-parse", "--show-toplevel")))
    if top != real:
        raise Fail(f"{repo_arg} is not the top level of a git work tree")
    return real


def _dirty(repo: str) -> dict[str, str]:
    out = _git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=no").stdout
    fields = out.split(b"\0")
    dirty: dict[str, str] = {}
    i = 0
    while i < len(fields) and fields[i]:
        entry = fields[i]
        xy, path = entry[:2].decode(), os.fsdecode(entry[3:])
        suffix = ""
        if "R" in xy or "C" in xy:
            i += 1
            suffix = f" from {os.fsdecode(fields[i])}"
        dirty[path] = f"{xy} {_fingerprint(repo, path)}{suffix}"
        i += 1
    return dirty


def take_snapshot(repo: str) -> dict:
    ref = _git(repo, "symbolic-ref", "-q", "HEAD", allow_fail=True)
    if ref.returncode not in (0, 1):
        raise Fail("git symbolic-ref failed")
    head = _git(repo, "rev-parse", "--verify", "-q", "HEAD^{commit}", allow_fail=True)
    if head.returncode != 0:
        raise Fail("HEAD has no commit")
    refs = {}
    for line in _text(_git(repo, "for-each-ref", "--format=%(refname)%00%(objectname)")).splitlines():
        name, oid = line.split("\0")
        refs[name] = oid
    worktrees = [
        os.fsdecode(line[len(b"worktree "):])
        for line in _git(repo, "worktree", "list", "--porcelain").stdout.splitlines()
        if line.startswith(b"worktree ")
    ]
    untracked = _git(repo, "ls-files", "--others", "--exclude-standard", "-z").stdout
    return {
        "version": VERSION,
        "repo": repo,
        "head": {"ref": _text(ref) if ref.returncode == 0 else None, "commit": _text(head)},
        "refs": refs,
        "config": _sha(_git(repo, "config", "--local", "--list", "-z").stdout),
        "worktrees": worktrees,
        "index": _sha(_git(repo, "ls-files", "--stage", "-z").stdout),
        "dirty": _dirty(repo),
        "untracked": sorted(os.fsdecode(p) for p in untracked.split(b"\0") if p),
    }


def _ref_violation(repo: str, name: str, before: str | None, after: str | None) -> dict:
    violation: dict = {"kind": "ref", "ref": name, "before": before, "after": after}
    reflog = None
    if after is not None:
        peeled = _git(repo, "rev-parse", "--verify", "-q", f"{after}^{{commit}}", allow_fail=True)
        if peeled.returncode == 0:
            fmt = "--format=%an <%ae>%x00%cn <%ce>%x00%cI%x00%s"
            author, committer, date, subject = _text(_git(repo, "log", "-1", fmt, after)).split("\0")
            violation["commit"] = {
                "author": author, "committer": committer, "date": date, "subject": subject,
            }
        reflog = _text(_git(repo, "reflog", "show", "-n1", "--format=%gn <%ge> | %gs", name)) or None
    violation["reflog"] = reflog
    if before is None:
        args = ["update-ref", "-d", name, after]
    elif after is None:
        args = ["update-ref", name, before, ""]
    else:
        args = ["update-ref", name, before, after]
    violation["restore"] = " ".join(shlex.quote(a) for a in ["git", "-C", repo, *args])
    return violation


def compare(repo: str, before: dict, allow: set[str]) -> dict:
    after = take_snapshot(repo)
    violations: list[dict] = []
    bh, ah = before["head"], after["head"]
    if bh["ref"] != ah["ref"] or (bh["ref"] is None and bh["commit"] != ah["commit"]):
        violations.append({"kind": "head", "before": bh, "after": ah})
    for name in sorted(set(before["refs"]) | set(after["refs"])):
        old, new = before["refs"].get(name), after["refs"].get(name)
        if old != new:
            violations.append(_ref_violation(repo, name, old, new))
    if before["config"] != after["config"]:
        violations.append({"kind": "config"})
    if before["worktrees"] != after["worktrees"]:
        violations.append(
            {"kind": "worktrees", "before": before["worktrees"], "after": after["worktrees"]}
        )
    if before["index"] != after["index"]:
        violations.append({"kind": "index"})
    for path in sorted(set(before["dirty"]) | set(after["dirty"])):
        old, new = before["dirty"].get(path), after["dirty"].get(path)
        if old != new and path not in allow:
            violations.append({"kind": "tracked", "path": path, "before": old, "after": new})
    current = set(after["untracked"])
    for path in sorted(set(before["untracked"]) - current - allow):
        violations.append({"kind": "untracked-removed", "path": path})
    touched = sorted(current - set(before["untracked"]) - allow)
    status = "changed" if violations else "unchanged"
    return {"status": status, "violations": violations, "touched": touched}


def _load(path: str, repo: str) -> dict:
    try:
        with open(path) as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        raise Fail(f"cannot read snapshot {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("version") != VERSION:
        raise Fail(f"snapshot {path} is not version {VERSION}")
    if os.path.realpath(str(data.get("repo"))) != repo:
        raise Fail(f"snapshot {path} belongs to another repo")
    return data


def run(args: argparse.Namespace) -> int:
    repo = _resolve_repo(args.repo)
    if args.command == "snapshot":
        out = os.path.realpath(args.out)
        if os.path.commonpath([out, repo]) == repo:
            raise Fail(f"{args.out} is inside the target repo")
        data = take_snapshot(repo)
        try:
            with open(out, "w") as handle:
                json.dump(data, handle, indent=2)
        except OSError as exc:
            raise Fail(f"cannot write {args.out}: {exc}") from exc
        return 0
    report = compare(repo, _load(args.before, repo), set(args.allow))
    print(json.dumps(report, indent=2))
    return 1 if report["violations"] else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="target_snapshot.py")
    sub = parser.add_subparsers(dest="command", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("repo")
    snap.add_argument("out")
    comp = sub.add_parser("compare")
    comp.add_argument("repo")
    comp.add_argument("before")
    comp.add_argument("--allow", action="append", default=[])
    args = parser.parse_args(argv[1:])
    try:
        return run(args)
    except Fail as exc:
        print(f"target_snapshot: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"target_snapshot: unexpected {exc!r}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
