# agoge

## Commands

- All checks: `dev/bin/release-checks`
- Format before each commit that touches Python: `uv run --with ruff ruff format skills/run-agoge/scripts`, then `uv run --with ruff ruff check --fix skills/run-agoge/scripts`. `dev/bin/release-checks` and CI fail on an unformatted file.
