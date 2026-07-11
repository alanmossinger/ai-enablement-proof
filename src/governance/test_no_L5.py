"""CI-blocking test: L5 (AUTONOMOUS) is prohibited.

This test is a required merge check. If any code path attempts an L5 action,
the build fails. Governance as a merge blocker, not a slide.
"""

import re
from pathlib import Path

import pytest

from src.governance.autonomy import AutonomyLevel, check_autonomy

SRC_ROOT = Path(__file__).resolve().parent.parent


# --- Behavioral tests ---


def test_l5_raises_value_error():
    """Requesting L5 autonomy must raise ValueError."""
    with pytest.raises(ValueError, match="L5.*prohibited"):
        check_autonomy("any_action", AutonomyLevel.AUTONOMOUS)


def test_l5_blocked_for_every_action_class():
    """L5 must be blocked for every defined action class."""
    from src.governance.autonomy import MAX_PERMITTED_LEVEL

    for action_class in MAX_PERMITTED_LEVEL:
        with pytest.raises(ValueError, match="L5.*prohibited"):
            check_autonomy(action_class, AutonomyLevel.AUTONOMOUS)


def test_no_action_class_permits_l5():
    """No action class in the permission table has L5 as max."""
    from src.governance.autonomy import MAX_PERMITTED_LEVEL

    for action_class, max_level in MAX_PERMITTED_LEVEL.items():
        assert max_level < AutonomyLevel.AUTONOMOUS, (
            f"Action class '{action_class}' has max level L5 (AUTONOMOUS). "
            "This is a governance violation."
        )


# --- Static analysis: scan source for L5 grants ---


def test_no_source_grants_l5():
    """Scan all Python source files for code that grants or permits L5.

    This catches attempts to bypass the governance layer by hardcoding
    AutonomyLevel.AUTONOMOUS or the integer 5 in autonomy contexts.
    """
    violations = []
    # Patterns that would indicate L5 grant attempts
    l5_patterns = [
        re.compile(r"AutonomyLevel\.AUTONOMOUS\s*[^)]"),  # Usage outside checks
        re.compile(r"MAX_PERMITTED_LEVEL\[.*\]\s*=\s*.*5"),
        re.compile(r"MAX_PERMITTED_LEVEL\[.*\]\s*=\s*.*AUTONOMOUS"),
    ]

    for py_file in SRC_ROOT.rglob("*.py"):
        # Skip this test file and the autonomy module (which defines L5 to prohibit it)
        if py_file.name in ("test_no_L5.py", "autonomy.py"):
            continue

        source = py_file.read_text(encoding="utf-8")
        for pattern in l5_patterns:
            matches = pattern.findall(source)
            if matches:
                violations.append(
                    f"{py_file.relative_to(SRC_ROOT)}: pattern {pattern.pattern} matched"
                )

    assert not violations, "Source files contain potential L5 autonomy grants:\n" + "\n".join(
        f"  - {v}" for v in violations
    )
