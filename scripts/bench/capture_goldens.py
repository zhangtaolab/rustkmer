#!/usr/bin/env python3
"""Immutable pre-refactor golden capture (05-03, OUT-02 Phase 8 input).

Rehashes the 12 COMMITTED golden `.rkdb` fixtures
(k in {21, 32, 64} x canonical x sorted) under tests/fixtures/ and asserts
equality with tests/fixtures/golden_manifest.sha256. The fixtures and the
manifest are immutable pre-refactor ground truth (v1.0 D-10 / DENSE-02
discipline): this script only READS them — it never runs the ignored
fixture-generator test binary and never writes to tests/fixtures/. ANY
hash mismatch is fixture tampering, a blocking finding that exits 1
loudly naming the fixture — never a reason to update the manifest.

Also runs `cargo test --locked --test golden_sha256_tests` (list-form
subprocess) and records its return code. Exit 0 only when all 12 hashes
match AND the golden test returncode is 0.

NOTE: static rehashing detects fixture tampering only — it does not
exercise the production write path. Phase 8 (OUT-02) still requires an
actual old-vs-new write-path differential against an independent
reference.

Python 3.11+ stdlib only.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    # Executed as a script (python3 scripts/bench/capture_goldens.py): the
    # repo root is not on sys.path yet. Insert it BEFORE importing so the
    # harness package resolves to this checkout in one shot (compare.py's
    # fixup, replicated).
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.bench.bench import binary_provenance

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
MANIFEST_PATH = FIXTURES_DIR / "golden_manifest.sha256"
EXPECTED_FIXTURE_COUNT = 12
SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
GOLDEN_TEST_CMD = ["cargo", "test", "--locked", "--test", "golden_sha256_tests"]

EXIT_OK = 0
EXIT_MISMATCH = 1
EXIT_INVALID = 2


def sha256_of(path):
    """Chunked sha256 of a file's actual bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest():
    """Parse the committed manifest into ordered (name, sha256) pairs.

    Malformed manifests (bad hex, duplicate names, wrong entry count) are
    invalid input (exit 2), distinct from a fixture whose bytes drifted
    (exit 1, tampering).
    """
    entries = []
    seen = set()
    for line in MANIFEST_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"malformed manifest line: {line!r}")
        name, hexdigest = parts
        if not SHA256_HEX_RE.match(hexdigest):
            raise ValueError(f"manifest entry {name!r}: not a 64-char sha256")
        if name in seen:
            raise ValueError(f"duplicate manifest entry: {name!r}")
        seen.add(name)
        entries.append((name, hexdigest))
    if len(entries) != EXPECTED_FIXTURE_COUNT:
        raise ValueError(
            f"manifest must list exactly {EXPECTED_FIXTURE_COUNT} fixtures, "
            f"got {len(entries)}")
    return entries


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Capture the 12 committed golden .rkdb hashes with "
                    "provenance (never regenerates fixtures).")
    parser.add_argument("--out", required=True,
                        help="path for the golden_capture.json artifact")
    parser.add_argument("--rustkmer",
                        default=str(REPO_ROOT / "target" / "release" / "rustkmer"),
                        help="rustkmer binary for provenance "
                             "(default: target/release/rustkmer)")
    args = parser.parse_args(argv)

    try:
        entries = load_manifest()
    except (OSError, ValueError) as exc:
        print(f"capture_goldens.py: invalid manifest: {exc}", file=sys.stderr)
        return EXIT_INVALID

    # Rehash every committed fixture and assert manifest equality BEFORE
    # anything else: tampering is a blocking finding, never a recapture.
    fixtures = []
    for name, expected in entries:
        path = FIXTURES_DIR / name
        try:
            actual = sha256_of(path)
        except OSError as exc:
            print(f"capture_goldens.py: FIXTURE MISSING/UNREADABLE: {name}: "
                  f"{exc}", file=sys.stderr)
            return EXIT_MISMATCH
        if actual != expected:
            print(f"capture_goldens.py: FIXTURE TAMPERED: {name}: "
                  f"manifest {expected} != actual {actual} — revert the "
                  "drift; never update the manifest to make this pass",
                  file=sys.stderr)
            return EXIT_MISMATCH
        fixtures.append({"name": name, "sha256": actual})

    # The committed golden test binary, run as-is (list form, no shell).
    proc = subprocess.run(GOLDEN_TEST_CMD, cwd=str(REPO_ROOT),
                          capture_output=True, text=True)

    doc = {
        "schema_version": 1,
        "captured": datetime.now(timezone.utc).isoformat(),
        "provenance": binary_provenance(args.rustkmer, "release"),
        "manifest_sha256": sha256_of(MANIFEST_PATH),
        "fixtures": fixtures,
        "golden_sha256_test": {
            "command": GOLDEN_TEST_CMD,
            "returncode": proc.returncode,
        },
        "note": "Static rehashing detects fixture tampering only — it does "
                "not exercise the production write path. Phase 8 (OUT-02) "
                "still requires an actual old-vs-new write-path "
                "differential against an independent reference.",
    }
    out_path = Path(args.out)
    with open(out_path, "w") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")

    if proc.returncode != 0:
        print(f"capture_goldens.py: golden test failed rc={proc.returncode}: "
              f"{GOLDEN_TEST_CMD}\ntrailing stderr:\n{proc.stderr[-500:]}",
              file=sys.stderr)
        return EXIT_MISMATCH
    print(f"capture_goldens.py: captured {len(fixtures)} golden hashes to "
          f"{out_path} (manifest equality proven, golden test rc=0)")
    return EXIT_OK


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        # Infra failures exit 2, never 1 (05-01 discipline).
        print(f"capture_goldens.py: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        sys.exit(EXIT_INVALID)
