"""Unit tests for the OUT-03 mutation-RED driver (08-03 Task 3).

The driver's exit codes are the experiment contract, so every verdict path is
exercised with an injected gate runner and blob hasher — no cargo is spawned,
nothing sleeps, and every file write lands under a temporary directory.

Pinned contracts:

* unique-match enforcement — zero and multiple occurrences are invalid (2),
  one occurrence is replaced;
* restore-in-finally — a raising gate runner still restores the exact bytes;
* the verdict matrix — all gates RED then GREEN is 0, a gate that stays green
  under mutation is 1, a non-unique find is 2, a gate failing without its
  expected substring is 2 (a spec bug never masks a real RED), a restore-blob
  mismatch is 2, and a gate not green after restore is 2;
* spec validation;
* evidence provenance — the recorded failure excerpt is a substring of the
  actual failing output, and the machine-greppable lines match the verdict.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Sequence

from scripts.bench import mutation_red

ORIGINAL = "alpha\nUNIQUE_TOKEN\nomega\n"
MUTATED = "alpha\nMUTATED_TOKEN\nomega\n"


def sha256_hasher(path: Path) -> str:
    """Deterministic blob hasher used in place of `git hash-object`."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_gate(
    test_name: str = "gate_one",
    expect_substring: str = "# expected red",
    test_bin: str = "gate_bin",
) -> dict[str, str]:
    """One gate definition."""
    return {
        "test_bin": test_bin,
        "test_name": test_name,
        "expect_substring": expect_substring,
    }


def make_spec(
    find: str = "UNIQUE_TOKEN",
    replace: str = "MUTATED_TOKEN",
    gates: Sequence[dict[str, str]] | None = None,
    name: str = "test-mutation",
) -> dict[str, object]:
    """One-mutation spec targeting `src/target.rs`."""
    return {
        "mutations": [
            {
                "name": name,
                "file": "src/target.rs",
                "find": find,
                "replace": replace,
                "gates": list(gates) if gates is not None else [make_gate()],
            }
        ]
    }


def state_runner(
    target: Path,
    original_text: str,
    red_output: str,
    green_on_mutated: Sequence[str] = (),
):
    """A fake gate runner keyed on the target file's current contents."""

    def runner(
        command: Sequence[str], cwd: Path
    ) -> "subprocess.CompletedProcess[str]":
        del cwd
        mutated = Path(target).read_text(encoding="utf-8") != original_text
        test_name = command[-1]
        if mutated and test_name not in green_on_mutated:
            return subprocess.CompletedProcess(command, 101, red_output, "")
        return subprocess.CompletedProcess(command, 0, "test result: ok\n", "")

    return runner


def always_failing_runner(red_output: str):
    """A gate runner that stays red even after the tree is restored."""

    def runner(
        command: Sequence[str], cwd: Path
    ) -> "subprocess.CompletedProcess[str]":
        del cwd
        return subprocess.CompletedProcess(command, 101, red_output, "")

    return runner


class MutationDriverTests(unittest.TestCase):
    """Every driver contract, driven with injected runners and hashers."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        source = self.root / "src"
        source.mkdir(parents=True)
        self.target = source / "target.rs"
        self.target.write_text(ORIGINAL, encoding="utf-8")
        self.out = self.root / "evidence.json"

    # -- unique-match enforcement ------------------------------------------

    def test_zero_occurrences_is_invalid(self) -> None:
        with self.assertRaises(mutation_red.InvalidExperiment):
            mutation_red.replace_unique(ORIGINAL, "ABSENT", "X", "m")

    def test_one_occurrence_is_replaced(self) -> None:
        self.assertEqual(
            mutation_red.replace_unique("a b a", "b", "c", "m"),
            "a c a",
        )

    def test_multiple_occurrences_is_invalid(self) -> None:
        with self.assertRaises(mutation_red.InvalidExperiment):
            mutation_red.replace_unique("a a", "a", "b", "m")

    def test_non_unique_find_exits_two(self) -> None:
        code, _stdout, stderr = self.invoke(
            make_spec(find="a", replace="Z"),
            state_runner(self.target, ORIGINAL, "# expected red"),
        )
        self.assertEqual(code, mutation_red.EXIT_INVALID)
        self.assertIn("MUTATION ERROR", stderr)
        self.assertFalse(self.out.exists(), "an invalid experiment writes no evidence")
        self.assertEqual(self.target.read_text(encoding="utf-8"), ORIGINAL)

    def test_zero_occurrence_find_exits_two(self) -> None:
        code, _stdout, _stderr = self.invoke(
            make_spec(find="ABSENT", replace="Z"),
            state_runner(self.target, ORIGINAL, "# expected red"),
        )
        self.assertEqual(code, mutation_red.EXIT_INVALID)
        self.assertEqual(self.target.read_text(encoding="utf-8"), ORIGINAL)

    def test_missing_file_exits_two(self) -> None:
        spec = make_spec()
        spec["mutations"][0]["file"] = "src/missing.rs"
        code, _stdout, _stderr = self.invoke(
            spec, state_runner(self.target, ORIGINAL, "# expected red")
        )
        self.assertEqual(code, mutation_red.EXIT_INVALID)

    # -- restore-in-finally ------------------------------------------------

    def test_restore_in_finally_when_runner_raises(self) -> None:
        def runner(
            command: Sequence[str], cwd: Path
        ) -> "subprocess.CompletedProcess[str]":
            del command, cwd
            raise RuntimeError("runner exploded")

        with self.assertRaises(RuntimeError):
            mutation_red.run_spec(
                make_spec(),
                root=self.root,
                gate_runner=runner,
                blob_hasher=sha256_hasher,
            )
        self.assertEqual(self.target.read_text(encoding="utf-8"), ORIGINAL)
        self.assertFalse(self.out.exists())

    def test_restore_blob_mismatch_is_invalid(self) -> None:
        class FlippingHasher:
            """pre, post, then a mismatching restore hash."""

            def __init__(self) -> None:
                self.calls = 0

            def __call__(self, path: Path) -> str:
                del path
                self.calls += 1
                return {1: "pre", 2: "post"}.get(self.calls, "different")

        code, _stdout, stderr = self.invoke(
            make_spec(),
            state_runner(self.target, ORIGINAL, "# expected red"),
            hasher=FlippingHasher(),
        )
        self.assertEqual(code, mutation_red.EXIT_INVALID)
        self.assertIn("restored blob", stderr)
        self.assertEqual(self.target.read_text(encoding="utf-8"), ORIGINAL)

    def test_post_restore_gate_failure_is_invalid(self) -> None:
        code, _stdout, stderr = self.invoke(
            make_spec(),
            always_failing_runner("# expected red"),
        )
        self.assertEqual(code, mutation_red.EXIT_INVALID)
        self.assertIn("did not return GREEN after restore", stderr)
        self.assertEqual(self.target.read_text(encoding="utf-8"), ORIGINAL)

    # -- verdict matrix ----------------------------------------------------

    def test_all_gates_red_then_green_exits_zero(self) -> None:
        red_output = "# expected red one\n# expected red two\n"
        gates = [
            make_gate(test_name="gate_one", expect_substring="# expected red one"),
            make_gate(test_name="gate_two", expect_substring="# expected red two"),
        ]
        code, stdout, stderr = self.invoke(
            make_spec(gates=gates),
            state_runner(self.target, ORIGINAL, red_output),
        )
        self.assertEqual(code, mutation_red.EXIT_GREEN, stderr)
        self.assertIn("MUTATION test-mutation result=RED restored=ok", stdout)
        self.assertIn("MUTATION VERDICT result=GREEN", stdout)

        evidence = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(evidence["verdict"]["result"], "GREEN")
        self.assertEqual(len(evidence["mutations"]), 1)
        mutation = evidence["mutations"][0]
        self.assertEqual(mutation["name"], "test-mutation")
        self.assertEqual(mutation["file"], "src/target.rs")
        self.assertEqual(mutation["find"], "UNIQUE_TOKEN")
        self.assertEqual(mutation["replace"], "MUTATED_TOKEN")
        self.assertTrue(mutation["restored_blob_matches"])
        self.assertNotEqual(mutation["pre_blob"], mutation["post_blob"])
        self.assertEqual(len(mutation["gates"]), 2)
        for gate in mutation["gates"]:
            self.assertEqual(gate["observed_exit"], 101)
            self.assertTrue(gate["expect_substring_seen"])
            self.assertEqual(gate["post_restore_exit"], 0)
        self.assertEqual(self.target.read_text(encoding="utf-8"), ORIGINAL)

    def test_gate_staying_green_exits_one(self) -> None:
        red_output = "# expected red one\n# expected red two\n"
        gates = [
            make_gate(test_name="gate_one", expect_substring="# expected red one"),
            make_gate(test_name="gate_two", expect_substring="# expected red two"),
        ]
        code, stdout, _stderr = self.invoke(
            make_spec(gates=gates),
            state_runner(
                self.target, ORIGINAL, red_output, green_on_mutated=("gate_two",)
            ),
        )
        self.assertEqual(code, mutation_red.EXIT_GATE_STAYED_GREEN)
        self.assertIn("MUTATION test-mutation result=GREEN restored=ok", stdout)
        self.assertIn("MUTATION VERDICT result=RED", stdout)

        evidence = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(evidence["verdict"]["result"], "RED")
        observed = {gate["test_name"]: gate for gate in evidence["mutations"][0]["gates"]}
        self.assertEqual(observed["gate_one"]["observed_exit"], 101)
        self.assertTrue(observed["gate_one"]["expect_substring_seen"])
        self.assertEqual(observed["gate_two"]["observed_exit"], 0)
        self.assertFalse(observed["gate_two"]["expect_substring_seen"])
        self.assertEqual(self.target.read_text(encoding="utf-8"), ORIGINAL)

    def test_gate_failing_without_expected_substring_is_invalid(self) -> None:
        code, _stdout, stderr = self.invoke(
            make_spec(),
            state_runner(self.target, ORIGINAL, "some unrelated failure\n"),
        )
        self.assertEqual(code, mutation_red.EXIT_INVALID)
        self.assertIn("lacks the expected substring", stderr)
        self.assertEqual(self.target.read_text(encoding="utf-8"), ORIGINAL)

    # -- evidence provenance ----------------------------------------------

    def test_evidence_excerpt_comes_from_the_actual_output(self) -> None:
        red_output = (
            "running 1 test\n"
            "thread 'gate_one' panicked at tests/x.rs:7:5:\n"
            "# expected red: the records are not ascending\n"
            "test gate_one ... FAILED\n"
        )
        code, _stdout, _stderr = self.invoke(
            make_spec(), state_runner(self.target, ORIGINAL, red_output)
        )
        self.assertEqual(code, mutation_red.EXIT_GREEN)
        gate = json.loads(self.out.read_text(encoding="utf-8"))["mutations"][0]["gates"][0]
        excerpt = gate["failure_excerpt"]
        self.assertIn(excerpt, red_output, "the excerpt must come from the observed output")
        self.assertIn("# expected red", excerpt)

    def test_machine_line_reports_restore_failure_only_on_mismatch(self) -> None:
        # The success path is covered above; here assert the GREEN line is
        # absent when the experiment is invalid.
        code, stdout, _stderr = self.invoke(
            make_spec(find="a", replace="Z"),
            state_runner(self.target, ORIGINAL, "# expected red"),
        )
        self.assertEqual(code, mutation_red.EXIT_INVALID)
        self.assertNotIn("MUTATION VERDICT", stdout)

    # -- spec validation ---------------------------------------------------

    def test_malformed_specs_are_invalid(self) -> None:
        malformed = [
            {},
            {"mutations": []},
            {"mutations": [{"name": "m", "file": "src/target.rs", "find": "a"}]},
            {
                "mutations": [
                    {
                        "name": "m",
                        "file": "src/target.rs",
                        "find": "UNIQUE_TOKEN",
                        "replace": "X",
                        "gates": [],
                    }
                ]
            },
            {
                "mutations": [
                    {
                        "name": "m",
                        "file": "src/target.rs",
                        "find": "UNIQUE_TOKEN",
                        "replace": "X",
                        "gates": [{"test_bin": "b", "test_name": "n"}],
                    }
                ]
            },
            {"mutations": "not-a-list"},
        ]

        def never_called(
            command: Sequence[str], cwd: Path
        ) -> "subprocess.CompletedProcess[str]":
            del command, cwd
            raise AssertionError("an invalid spec must never run a gate")

        for spec in malformed:
            with self.subTest(spec=spec):
                self.target.write_text(ORIGINAL, encoding="utf-8")
                code, _stdout, stderr = self.invoke(spec, never_called)
                self.assertEqual(code, mutation_red.EXIT_INVALID)
                self.assertIn("MUTATION ERROR", stderr)
                self.assertFalse(self.out.exists())

    def test_load_spec_rejects_missing_and_malformed_json(self) -> None:
        with self.assertRaises(mutation_red.InvalidExperiment):
            mutation_red.load_spec(self.root / "does-not-exist.json")
        bad = self.root / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        with self.assertRaises(mutation_red.InvalidExperiment):
            mutation_red.load_spec(bad)

    # -- helpers -----------------------------------------------------------

    def invoke(
        self,
        spec: dict[str, object],
        runner,
        hasher=sha256_hasher,
    ) -> tuple[int, str, str]:
        """Run `mutation_red.main` against a temp spec and capture its output."""
        spec_path = self.root / "spec.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = mutation_red.main(
                [
                    "run",
                    "--spec",
                    str(spec_path),
                    "--out",
                    str(self.out),
                    "--root",
                    str(self.root),
                ],
                gate_runner=runner,
                blob_hasher=hasher,
            )
        return code, stdout.getvalue(), stderr.getvalue()


if __name__ == "__main__":
    unittest.main()
