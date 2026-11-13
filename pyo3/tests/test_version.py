"""Stale-extension tripwire for the rebuilt ``pyrustkmer`` native module.

Deliberately has **no** module skip guard: an absent or stale extension must
FAIL here, not skip. The imported ``.so`` is the measured artifact for the
Phase 9 parity work, so a build without ``__version__`` (every build before
this phase) must be visible as a failure rather than silently accepted.
"""

import pathlib
import tomllib

import pyrustkmer

REPO = pathlib.Path(__file__).resolve().parents[2]


def _expected_version():
    """Return ``[project].version`` from ``pyo3/pyproject.toml``."""
    pyproject = REPO / "pyo3" / "pyproject.toml"
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]


def test_extension_version_attribute_is_present():
    """A rebuilt extension must export a non-empty ``__version__`` string."""
    observed = getattr(pyrustkmer, "__version__", None)
    assert isinstance(observed, str) and observed, (
        "stale or mismatched extension: pyrustkmer.__version__ is %r "
        "(module %r) — rebuild with `maturin develop --release "
        "--manifest-path pyo3/Cargo.toml` in .venv313"
        % (observed, getattr(pyrustkmer, "__file__", None))
    )


def test_extension_version_matches_pyproject():
    """The exported ``__version__`` must equal the manifest's version."""
    expected = _expected_version()
    observed = getattr(pyrustkmer, "__version__", None)
    assert observed == expected, (
        "stale or mismatched extension: observed __version__ %r != expected "
        "%r (module %r) — rebuild with `maturin develop --release "
        "--manifest-path pyo3/Cargo.toml` in .venv313"
        % (observed, expected, getattr(pyrustkmer, "__file__", None))
    )
