"""IA3 migrations (0008+) must downgrade and re-apply cleanly."""

import subprocess


def _alembic(*args: str) -> str:
    return subprocess.run(["alembic", *args], check=True, capture_output=True, text=True).stdout


def test_new_revisions_round_trip() -> None:
    head = _alembic("current").split()[0]

    _alembic("downgrade", "0007")
    _alembic("upgrade", "head")

    assert _alembic("current").split()[0] == head
