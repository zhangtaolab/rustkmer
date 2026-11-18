"""Stale-extension tripwire for the rebuilt ``pyrustkmer`` native module.

Deliberately has **no** module skip guard: an absent or stale extension must
FAIL here, not skip. The imported ``.so`` is the measured artifact for the
Phase 9 parity work, so a build without ``__version__`` (every build before
this phase) must be visible as a failure rather than silently accepted.

A structural tripwire lives beside the version checks: a ``pyrustkmer/``
package directory with ``__init__.py`` wins import resolution over a same-named
top-level extension file in the same import root, so a hand-copied ``.so``
beside a stale package directory is silently never imported. The helpers below
detect that coexistence from the filesystem alone; the tests pin them against
synthetic ``tmp_path`` layouts plus the live interpreter's import roots.
"""

import importlib.machinery
import pathlib
import sys
import sysconfig
import tomllib

import pyrustkmer

REPO = pathlib.Path(__file__).resolve().parents[2]


def _expected_version():
    """Return ``[project].version`` from ``pyo3/pyproject.toml``."""
    pyproject = REPO / "pyo3" / "pyproject.toml"
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]


def _shadowed_extension_files(import_root):
    """Return top-level extension files shadowed by a ``pyrustkmer`` package.

    Within one ``sys.path`` entry a package directory wins import resolution
    over a same-named extension module, so a ``pyrustkmer/`` directory carrying
    ``__init__.py`` silently shadows a top-level ``pyrustkmer.so`` beside it.
    The correct maturin layout nests the extension inside the package directory
    and is never flagged.
    """
    root = pathlib.Path(import_root)
    if not (root / "pyrustkmer" / "__init__.py").is_file():
        return []
    return [
        root / ("pyrustkmer" + suffix)
        for suffix in importlib.machinery.EXTENSION_SUFFIXES
        if (root / ("pyrustkmer" + suffix)).is_file()
    ]


def _import_roots():
    """Return the de-duplicated import roots worth scanning on this interpreter."""
    candidates = [
        pathlib.Path(entry) if entry else pathlib.Path.cwd() for entry in sys.path
    ]
    candidates.append(pathlib.Path(sysconfig.get_paths()["purelib"]))
    candidates.append(pathlib.Path(sysconfig.get_paths()["platlib"]))
    roots = []
    for candidate in candidates:
        if candidate.is_dir() and candidate not in roots:
            roots.append(candidate)
    return roots


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


def test_shadowing_guard_detects_hand_copied_extension(tmp_path):
    """The broken shape — package directory plus a top-level .so — is caught."""
    (tmp_path / "pyrustkmer").mkdir()
    (tmp_path / "pyrustkmer" / "__init__.py").write_text("", encoding="utf-8")
    extension = tmp_path / ("pyrustkmer" + importlib.machinery.EXTENSION_SUFFIXES[-1])
    extension.write_bytes(b"")
    assert _shadowed_extension_files(tmp_path) == [extension]


def test_shadowing_guard_accepts_the_maturin_layout(tmp_path):
    """The healthy maturin layout nests the extension inside the package."""
    package = tmp_path / "pyrustkmer"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    extension = package / ("pyrustkmer" + importlib.machinery.EXTENSION_SUFFIXES[-1])
    extension.write_bytes(b"")
    assert _shadowed_extension_files(tmp_path) == []


def test_shadowing_guard_ignores_absent_package(tmp_path):
    """No package directory means nothing can be shadowed."""
    assert _shadowed_extension_files(tmp_path) == []


def test_shadowing_guard_ignores_non_package_directory(tmp_path):
    """A directory without __init__.py does not shadow an extension file."""
    (tmp_path / "pyrustkmer").mkdir()
    extension = tmp_path / ("pyrustkmer" + importlib.machinery.EXTENSION_SUFFIXES[-1])
    extension.write_bytes(b"")
    assert _shadowed_extension_files(tmp_path) == []


def test_no_import_root_has_a_shadowed_extension():
    """The live interpreter must not carry a hidden hand-copied extension."""
    shadowed = []
    for root in _import_roots():
        for path in _shadowed_extension_files(root):
            if path not in shadowed:
                shadowed.append(path)
    assert not shadowed, (
        "shadowed extension(s): %s — a pyrustkmer/ package directory hides a "
        "top-level extension file in the same import root; rebuild with "
        "`maturin develop --release --manifest-path pyo3/Cargo.toml` and "
        "delete the stale package directory"
        % ", ".join(str(path) for path in shadowed)
    )
