"""SEC-04: free-text confirmation is parsed negation-first (interim until the confirm endpoint)."""

import pytest

from app.services.ai_engine.orchestrator import parse_confirmation


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("yes", "confirm"),
        ("Yes.", "confirm"),
        ("yep go ahead", "confirm"),
        ("ok", "confirm"),
        ("okay", "confirm"),
        ("sure", "confirm"),
        ("looks good", "confirm"),
        ("save it", "confirm"),
        ("confirm", "confirm"),
        ("correct, do it", "confirm"),
        ("no", "reject"),
        ("nope", "reject"),
        ("no, don't save", "reject"),
        ("no don't save", "reject"),
        ("do not save it", "reject"),
        ("not ok", "reject"),
        ("don't", "reject"),
        ("cancel", "reject"),
        ("stop", "reject"),
        ("yes but change the email", "reject"),
        ("change the email, ok?", "reject"),
        ("ok but fix the phone", "reject"),
        ("wrong name", "reject"),
        ("the phone is 98400 12345", "unclear"),
        ("hmm", "unclear"),
    ],
)
def test_confirmation_parser(text: str, expected: str) -> None:
    assert parse_confirmation(text) == expected
