"""Compatibility entry point for the mocked pytest suite; no AWS calls."""

import subprocess
import sys

raise SystemExit(
    subprocess.call(
        [sys.executable, "-m", "pytest", "tests/test_agenda.py", "tests/test_agenda_lambda.py", "-q"]
    )
)
