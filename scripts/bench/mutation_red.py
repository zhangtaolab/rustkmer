"""Mechanical mutation-RED driver for the Phase 8 output gates (OUT-03).

A gate that cannot fail reports nothing. This driver injects one defect at a
time into the production sources, runs the NAMED gates that are supposed to
catch it, and requires that every gate exits nonzero with its expected
assertion text in the output. It then restores the original bytes in a
``finally`` block, verifies the restored ``git hash-object`` blob equals the
pre-mutation blob, and re-runs every gate requiring exit 0.

The experiment is *mechanical*: a ``find`` string must occur EXACTLY once.
Zero or multiple occurrences is exit 2 (invalid experiment) — a mutation that
cannot be applied precisely proves nothing and is never recorded as a pass.

Exit codes:

* **0** — every mutation produced RED for every gate, and every gate is GREEN
  again after restore;
* **1** — a gate stayed green under a mutation (the gate cannot fail; this is
  a phase-level failure and is never softened);
* **2** — invalid experiment setup (missing file, non-unique ``find``,
  malformed spec, restore mismatch, a gate failed without the expected
  substring, or a gate was not green after restore).

Spec shape::

    {"mutations": [{"name": str, "file": str, "find": str, "replace": str,
                    "gates": [{"test_bin": str, "test_name": str,
                               "expect_substring": str}]}]}

Evidence shape (fixed so the phase verifier can read it)::

    {"mutations": [{"name", "file", "find", "replace", "pre_blob",
                    "post_blob", "restored_blob_matches",
                    "gates": [{"test_bin", "test_name", "command",
                               "observed_exit", "expect_substring_seen",
                               "failure_excerpt", "post_restore_exit"}]}],
     "verdict": {"result": "GREEN" | "RED"}}

Python 3.11 stdlib only. The gate runner is injectable so the unit tests never
spawn cargo.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

EXIT_GREEN = 0
EXIT_GATE_STAYED_GREEN = 1
EXIT_INVALID = 2

#: Excerpt size recorded around the expected failure substring.
EXCERPT_LIMIT = 2000

GateRunner = Callable[[Sequence[str], Path], "subprocess.CompletedProcess[str]"]
BlobHasher = Callable[[Path], str]


class InvalidExperiment(Exception):
    """The mutation experiment cannot be applied or verified precisely."""


def replace_unique(text: str, find: str, replace: str, label: str) -> str:
    """Replace exactly one occurrence of ``find`` with ``replace``.

    Raises:
        InvalidExperiment: when ``find`` occurs zero or multiple times.
    """
    if not find:
        raise InvalidExperiment(f"{label}: the find string is empty")
    occurrences = text.count(find)
    if occurrences == 0:
        raise InvalidExperiment(
            f"{label}: the find string does not occur in the file"
        )
    if occurrences > 1:
        raise InvalidExperiment(
            f"{label}: the find string occurs {occurrences} times; a mutation "
            "must target exactly one unique region"
        )
    return text.replace(find, replace, 1)


def failure_excerpt(output: str, expected: str, limit: int = EXCERPT_LIMIT) -> str:
    """Return an excerpt of ``output`` centred on ``expected``.

    The result is always a substring of ``output`` so the recorded evidence
    provably comes from the observed failure.
    """
    if not output:
        return ""
    index = output.find(expected)
    if index < 0:
        return output[-limit:]
    half = max(limit // 2, len(expected))
    start = max(0, index - half)
    end = min(len(output), index + len(expected) + half)
    return output[start:end]


def validate_spec(spec: Any) -> None:
    """Validate the spec shape; raise ``InvalidExperiment`` on any problem."""
    if not isinstance(spec, dict):
        raise InvalidExperiment("the spec must be a JSON object")
    mutations = spec.get("mutations")
    if not isinstance(mutations, list) or not mutations:
        raise InvalidExperiment("the spec must carry a non-empty 'mutations' list")
    for index, mutation in enumerate(mutations):
        label = f"mutation[{index}]"
        if not isinstance(mutation, dict):
            raise InvalidExperiment(f"{label} must be an object")
        for key in ("name", "file", "find", "replace"):
            value = mutation.get(key)
            if not isinstance(value, str) or not value:
                raise InvalidExperiment(f"{label}.{key} must be a non-empty string")
        gates = mutation.get("gates")
        if not isinstance(gates, list) or not gates:
            raise InvalidExperiment(f"{label}.gates must be a non-empty list")
        for gate_index, gate in enumerate(gates):
            gate_label = f"{label}.gates[{gate_index}]"
            if not isinstance(gate, dict):
                raise InvalidExperiment(f"{gate_label} must be an object")
            for key in ("test_bin", "test_name", "expect_substring"):
                value = gate.get(key)
                if not isinstance(value, str) or not value:
                    raise InvalidExperiment(
                        f"{gate_label}.{key} must be a non-empty string"
                    )


def load_spec(path: Path) -> dict[str, Any]:
    """Read and validate the JSON spec."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        raise InvalidExperiment(f"cannot read the spec {path}: {error}") from error
    try:
        spec = json.loads(text)
    except json.JSONDecodeError as error:
        raise InvalidExperiment(f"the spec {path} is not valid JSON: {error}") from error
    validate_spec(spec)
    return spec


def git_blob_hash(path: Path, root: Path) -> str:
    """Return the ``git hash-object`` value of the working-tree file."""
    result = subprocess.run(
        ["git", "-C", str(root), "hash-object", "--", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise InvalidExperiment(
            f"git hash-object failed for {path}: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def subprocess_gate_runner(
    command: Sequence[str], cwd: Path
) -> "subprocess.CompletedProcess[str]":
    """Run one gate with a list-form subprocess (never a shell)."""
    return subprocess.run(
        list(command),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def gate_command(gate: dict[str, Any]) -> list[str]:
    """The exact cargo invocation for one named gate."""
    return [
        "cargo",
        "test",
        "--locked",
        "--test",
        gate["test_bin"],
        gate["test_name"],
    ]


def combined_output(result: "subprocess.CompletedProcess[str]") -> str:
    """The gate's stdout and stderr as one observation string."""
    return (result.stdout or "") + (result.stderr or "")


def run_spec(
    spec: dict[str, Any],
    *,
    root: Path,
    gate_runner: GateRunner | None = None,
    blob_hasher: BlobHasher | None = None,
) -> tuple[int, dict[str, Any]]:
    """Apply every mutation, observe RED, restore, and require GREEN again.

    Returns:
        ``(exit_code, evidence)``. The evidence document is always built with
        the fixed phase-verifier shape.
    """
    validate_spec(spec)
    runner = gate_runner or subprocess_gate_runner
    hasher: BlobHasher = blob_hasher or (lambda path: git_blob_hash(path, root))

    mutations_out: list[dict[str, Any]] = []
    exit_code = EXIT_GREEN

    for mutation in spec["mutations"]:
        name = mutation["name"]
        path = (root / mutation["file"]).resolve()
        if not path.is_file():
            raise InvalidExperiment(f"{name}: the mutation target {path} is not a file")
        try:
            original = path.read_bytes()
            text = original.decode("utf-8")
        except OSError as error:
            raise InvalidExperiment(f"{name}: cannot read {path}: {error}") from error
        except UnicodeDecodeError as error:
            raise InvalidExperiment(f"{name}: {path} is not UTF-8: {error}") from error

        mutated_text = replace_unique(text, mutation["find"], mutation["replace"], name)
        mutated = mutated_text.encode("utf-8")
        pre_blob = hasher(path)
        gates_out: list[dict[str, Any]] = []
        all_gates_red = True
        post_blob = ""

        try:
            path.write_bytes(mutated)
            post_blob = hasher(path)
            if post_blob == pre_blob:
                raise InvalidExperiment(
                    f"{name}: the mutation did not change the file's blob hash"
                )
            for gate in mutation["gates"]:
                command = gate_command(gate)
                observed = runner(command, root)
                observed_output = combined_output(observed)
                substring_seen = gate["expect_substring"] in observed_output
                gates_out.append(
                    {
                        "test_bin": gate["test_bin"],
                        "test_name": gate["test_name"],
                        "command": command,
                        "observed_exit": observed.returncode,
                        "expect_substring_seen": substring_seen,
                        "failure_excerpt": failure_excerpt(
                            observed_output, gate["expect_substring"]
                        ),
                        "post_restore_exit": None,
                    }
                )
                if observed.returncode == 0:
                    all_gates_red = False
                elif not substring_seen:
                    raise InvalidExperiment(
                        f"{name}: gate {gate['test_bin']}::{gate['test_name']} failed "
                        "but its output lacks the expected substring "
                        f"{gate['expect_substring']!r} — the spec text is wrong, and a "
                        "real RED must never be masked as a spec bug"
                    )
        finally:
            path.write_bytes(original)

        restored_blob = hasher(path)
        restored_blob_matches = restored_blob == pre_blob
        if not restored_blob_matches:
            raise InvalidExperiment(
                f"{name}: the restored blob {restored_blob} does not match the "
                f"pre-mutation blob {pre_blob}"
            )

        for gate, gate_out in zip(mutation["gates"], gates_out):
            restored = runner(gate_command(gate), root)
            gate_out["post_restore_exit"] = restored.returncode
            if restored.returncode != 0:
                raise InvalidExperiment(
                    f"{name}: gate {gate['test_bin']}::{gate['test_name']} did not "
                    f"return GREEN after restore (exit {restored.returncode})"
                )

        mutation_result = "RED" if all_gates_red else "GREEN"
        if not all_gates_red:
            exit_code = EXIT_GATE_STAYED_GREEN
        print(
            f"MUTATION {name} result={mutation_result} "
            f"restored={'ok' if restored_blob_matches else 'failed'}"
        )
        mutations_out.append(
            {
                "name": name,
                "file": mutation["file"],
                "find": mutation["find"],
                "replace": mutation["replace"],
                "pre_blob": pre_blob,
                "post_blob": post_blob,
                "restored_blob_matches": restored_blob_matches,
                "gates": gates_out,
            }
        )

    verdict = "GREEN" if exit_code == EXIT_GREEN else "RED"
    print(f"MUTATION VERDICT result={verdict}")
    evidence = {"mutations": mutations_out, "verdict": {"result": verdict}}
    return exit_code, evidence


def write_evidence(path: Path, evidence: dict[str, Any]) -> None:
    """Write the evidence document (fixed shape) as indented JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Mechanically prove the Phase 8 output gates can fail."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser(
        "run", help="apply the spec's mutations, observe RED, restore, re-green"
    )
    run.add_argument("--spec", required=True, type=Path, help="mutation spec JSON")
    run.add_argument("--out", required=True, type=Path, help="evidence JSON output")
    run.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root the spec's file paths are relative to",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    gate_runner: GateRunner | None = None,
    blob_hasher: BlobHasher | None = None,
) -> int:
    """CLI entry point. Returns the exit code (0 GREEN, 1 gate-stayed-green, 2 invalid)."""
    args = build_parser().parse_args(argv)
    try:
        spec = load_spec(args.spec)
        exit_code, evidence = run_spec(
            spec,
            root=args.root,
            gate_runner=gate_runner,
            blob_hasher=blob_hasher,
        )
        write_evidence(args.out, evidence)
    except InvalidExperiment as error:
        print(f"MUTATION ERROR {error}", file=sys.stderr)
        return EXIT_INVALID
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
