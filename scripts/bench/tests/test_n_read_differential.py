#!/usr/bin/env python3
"""Unit suite for n_read_differential.py (05-06, PROF-05, TDD).

Pure map-difference reduction, deterministic fixture construction, stable
ordering, verdict semantics, and invalid-artifact exit-2 cases — all tested
WITHOUT PyO3 (the real CLI/PyO3 execution stays opt-in via the controller).
The guarded import keeps RED a genuine planned-behavior failure rather than
a collection/import fault (05-05 precedent).
"""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

try:
    from scripts.bench import n_read_differential as nrd
    IMPLEMENTED = True
except ImportError:
    nrd = None
    IMPLEMENTED = False


class ImplementedGate(unittest.TestCase):
    """RED guard: every planned-behavior test asserts implementation first."""

    def require(self):
        self.assertTrue(
            IMPLEMENTED, "n_read_differential not implemented yet (05-06)")


class TestMapDiff(ImplementedGate):
    """Pure symmetric-difference reduction on hand-built count maps."""

    def test_equal_maps_produce_zero_diffs(self):
        self.require()
        m = {"ACGT" * 5 + "A": 3, "TTTT" * 5 + "C": 1}
        d = nrd.diff_maps(m, dict(m))
        self.assertEqual(d["python_only"], [])
        self.assertEqual(d["cli_only"], [])
        self.assertEqual(d["count_deltas"], [])
        self.assertEqual(d["cli"], {"distinct": 2, "total": 4})
        self.assertEqual(d["python"], {"distinct": 2, "total": 4})

    def test_python_only_chimeric_key(self):
        self.require()
        cli = {"A" * 21: 2}
        py = {"A" * 21: 2, "C" * 21: 1}
        d = nrd.diff_maps(cli, py)
        self.assertEqual(d["python_only"], ["C" * 21])
        self.assertEqual(d["cli_only"], [])
        self.assertEqual(d["count_deltas"], [])
        self.assertEqual(d["example_chimeras"], ["C" * 21])
        self.assertEqual(d["python"], {"distinct": 2, "total": 3})

    def test_cli_only_missing_key(self):
        self.require()
        cli = {"A" * 21: 2, "G" * 21: 5}
        py = {"A" * 21: 2}
        d = nrd.diff_maps(cli, py)
        self.assertEqual(d["python_only"], [])
        self.assertEqual(d["cli_only"], ["G" * 21])
        self.assertEqual(d["cli"], {"distinct": 2, "total": 7})
        self.assertEqual(d["python"], {"distinct": 1, "total": 2})

    def test_shared_key_count_delta(self):
        self.require()
        cli = {"A" * 21: 2}
        py = {"A" * 21: 5}
        d = nrd.diff_maps(cli, py)
        self.assertEqual(d["python_only"], [])
        self.assertEqual(d["cli_only"], [])
        self.assertEqual(d["count_deltas"],
                         [{"kmer": "A" * 21, "cli": 2, "python": 5}])

    def test_stable_ordering_and_example_cap(self):
        self.require()
        # Insertion order deliberately unsorted; output must be sorted.
        keys = ["A" * 21, "C" * 21, "G" * 21, "T" * 21,
                "AC" * 10 + "A", "GT" * 10 + "G"]
        py = {k: 1 for k in reversed(keys)}
        d = nrd.diff_maps({}, py)
        self.assertEqual(d["python_only"], sorted(py))
        self.assertEqual(d["example_chimeras"], sorted(py)[:5])
        self.assertEqual(len(d["example_chimeras"]), 5)
        # JSON round-trip is order-stable regardless of dict insertion order.
        a = json.dumps(nrd.diff_maps({}, py), sort_keys=True)
        b = json.dumps(nrd.diff_maps({}, dict(reversed(list(py.items())))),
                       sort_keys=True)
        self.assertEqual(a, b)

    def test_empty_maps_are_equal(self):
        self.require()
        d = nrd.diff_maps({}, {})
        self.assertEqual(d["python_only"], [])
        self.assertEqual(d["cli_only"], [])
        self.assertEqual(d["cli"], {"distinct": 0, "total": 0})


class TestFixtures(ImplementedGate):
    """Deterministic four-line FASTQ cases at k=21 with exact N positions."""

    def test_nine_cases_with_exact_names(self):
        self.require()
        cases = nrd.build_cases()
        self.assertEqual([c["name"] for c in cases], [
            "control_no_n", "n_at_first", "n_at_window_end",
            "n_at_window_start", "n_at_last", "multiple_n", "lowercase_n",
            "record_boundary", "short_read"])

    def test_requested_n_positions_present(self):
        self.require()
        cases = {c["name"]: c["reads"] for c in nrd.build_cases()}
        self.assertEqual(cases["n_at_first"][0][0], "N")
        self.assertEqual(cases["n_at_window_end"][0][20], "N")
        self.assertEqual(cases["n_at_window_start"][0][21], "N")
        self.assertEqual(cases["n_at_last"][0][29], "N")
        multi = cases["multiple_n"][0]
        self.assertEqual([i for i, b in enumerate(multi) if b == "N"],
                         [5, 15, 25])
        self.assertEqual(cases["lowercase_n"][0][10], "n")
        boundary = cases["record_boundary"]
        self.assertEqual(len(boundary), 2)
        self.assertEqual(boundary[0][24], "N")
        self.assertEqual(boundary[1][0], "N")
        self.assertEqual(len(boundary[0]), 25)
        self.assertEqual(len(boundary[1]), 25)

    def test_control_has_no_n_and_short_read_below_k(self):
        self.require()
        cases = {c["name"]: c["reads"] for c in nrd.build_cases()}
        for seq in cases["control_no_n"]:
            self.assertNotIn("N", seq)
            self.assertNotIn("n", seq)
            self.assertEqual(len(seq), 30)
        self.assertEqual(len(cases["short_read"][0]), 15)
        self.assertLess(len(cases["short_read"][0]), 21)

    def test_fastq_four_line_shape_and_quality_length(self):
        self.require()
        for case in nrd.build_cases():
            data = nrd.fastq_bytes(case)
            lines = data.decode().splitlines()
            self.assertEqual(len(lines), 4 * len(case["reads"]))
            for i in range(len(case["reads"])):
                header, seq, plus, qual = lines[4 * i:4 * i + 4]
                self.assertTrue(header.startswith("@"))
                self.assertEqual(seq, case["reads"][i])
                self.assertTrue(plus.startswith("+"))
                self.assertEqual(len(qual), len(seq))
                self.assertEqual(qual, "I" * len(seq))

    def test_fastq_bytes_are_deterministic(self):
        self.require()
        for case in nrd.build_cases():
            self.assertEqual(nrd.fastq_bytes(case), nrd.fastq_bytes(case))


def case_record(name, python_only=(), cli_only=(), count_deltas=()):
    return {"name": name, "python_only": list(python_only),
            "cli_only": list(cli_only), "count_deltas": list(count_deltas)}


class TestEvaluate(ImplementedGate):
    """Verdict semantics: control gate, divergence recording, unified mode."""

    def divergent_cases(self):
        return [case_record("control_no_n"),
                case_record("n_at_window_end", python_only=["C" * 21])]

    def test_divergence_mode_records_and_passes(self):
        self.require()
        code, lines = nrd.evaluate(self.divergent_cases(), "divergence")
        self.assertEqual(code, 0)
        self.assertTrue(any("control_no_n" in line for line in lines))

    def test_control_mismatch_exits_1(self):
        self.require()
        cases = [case_record("control_no_n", python_only=["A" * 21]),
                 case_record("n_at_window_end", python_only=["C" * 21])]
        code, _ = nrd.evaluate(cases, "divergence")
        self.assertEqual(code, 1)

    def test_control_count_delta_exits_1(self):
        self.require()
        cases = [case_record("control_no_n",
                             count_deltas=[{"kmer": "A" * 21, "cli": 1,
                                            "python": 2}])]
        code, _ = nrd.evaluate(cases, "divergence")
        self.assertEqual(code, 1)

    def test_no_divergence_exits_1_in_divergence_mode(self):
        self.require()
        cases = [case_record("control_no_n"), case_record("n_at_first")]
        code, _ = nrd.evaluate(cases, "divergence")
        self.assertEqual(code, 1)

    def test_unified_mode_all_equal_passes(self):
        self.require()
        cases = [case_record("control_no_n"), case_record("n_at_first")]
        code, _ = nrd.evaluate(cases, "unified")
        self.assertEqual(code, 0)

    def test_unified_mode_with_divergence_exits_1(self):
        self.require()
        code, _ = nrd.evaluate(self.divergent_cases(), "unified")
        self.assertEqual(code, 1)

    def test_empty_records_raise(self):
        self.require()
        with self.assertRaises(ValueError):
            nrd.evaluate([], "divergence")

    def test_missing_control_raises(self):
        self.require()
        with self.assertRaises(ValueError):
            nrd.evaluate([case_record("n_at_first")], "divergence")

    def test_duplicate_control_raises(self):
        self.require()
        with self.assertRaises(ValueError):
            nrd.evaluate([case_record("control_no_n"),
                          case_record("control_no_n")], "divergence")


def run_main(argv):
    """Run nrd.main with captured output; SystemExit maps to its code."""
    import contextlib
    import io
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = nrd.main(argv)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class TestInvalidArtifacts(ImplementedGate):
    """Invalid runs exit 2 — never an empty PASS (no PyO3 needed)."""

    def run_main(self, argv):
        return run_main(argv)

    def test_missing_rustkmer_binary_exits_2(self):
        self.require()
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = self.run_main(
                ["--rustkmer", str(Path(tmp) / "absent-rustkmer"),
                 "--out", str(Path(tmp) / "out.json")])
            self.assertEqual(code, 2)
            self.assertFalse(Path(tmp, "out.json").exists())

    def test_missing_extension_exits_2(self):
        self.require()
        # Under the system python3 (no PyO3), a valid binary path still
        # cannot produce a differential: the missing extension is invalid.
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = self.run_main(
                ["--rustkmer", sys.executable,
                 "--out", str(Path(tmp) / "out.json")])
            self.assertEqual(code, 2)
            self.assertIn("pyrustkmer", err)
            self.assertFalse(Path(tmp, "out.json").exists())


class TestUnifiedSemantics(ImplementedGate):
    """The recorded semantics literal is the post-D2 unified one."""

    def test_expected_semantics_is_unified(self):
        self.require()
        self.assertEqual(
            nrd.EXPECTED_SEMANTICS,
            {"cli": "skip-N-windows", "python": "skip-N-windows"})


class TestPreviousLoading(ImplementedGate):
    """--previous validates a prior artifact before embedding it as `before`."""

    def valid_prior(self):
        return {
            "schema_version": 1,
            "k": nrd.K,
            "canonical": True,
            "expectation": "divergence",
            "totals": {
                "cases": len(nrd.build_cases()),
                "python_only_total": 33,
                "cli_only_total": 0,
                "count_delta_total": 0,
                "divergent_cases": ["n_at_window_end", "n_at_window_start",
                                    "multiple_n", "lowercase_n"],
            },
            "cases": [
                {"name": case["name"],
                 "cli": {"distinct": 2, "total": 10},
                 "python": {"distinct": 3, "total": 12}}
                for case in nrd.build_cases()
            ],
        }

    def write_prior(self, tmp, doc, name="prior.json"):
        path = Path(tmp) / name
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def assert_invalid(self, tmp, prior):
        path = self.write_prior(tmp, prior)
        with self.assertRaises(ValueError):
            nrd.load_previous(path)

    def test_valid_prior_embeds_path_sha256_totals_and_cases(self):
        self.require()
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_prior(tmp, self.valid_prior())
            prior = nrd.load_previous(path)
            self.assertEqual(prior["path"], str(path))
            self.assertEqual(prior["sha256"],
                             hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(prior["expectation"], "divergence")
            self.assertEqual(prior["totals"]["python_only_total"], 33)
            self.assertEqual(
                prior["cases"]["control_no_n"],
                {"cli": {"distinct": 2, "total": 10},
                 "python": {"distinct": 3, "total": 12}})
            self.assertEqual(set(prior["cases"]),
                             {c["name"] for c in nrd.build_cases()})

    def test_k_mismatch_raises(self):
        self.require()
        prior = self.valid_prior()
        prior["k"] = nrd.K + 2
        with tempfile.TemporaryDirectory() as tmp:
            self.assert_invalid(tmp, prior)

    def test_canonical_not_true_raises(self):
        self.require()
        for value in (False, "true", None):
            prior = self.valid_prior()
            prior["canonical"] = value
            with tempfile.TemporaryDirectory() as tmp:
                self.assert_invalid(tmp, prior)

    def test_missing_case_name_raises(self):
        self.require()
        prior = self.valid_prior()
        prior["cases"].pop()
        with tempfile.TemporaryDirectory() as tmp:
            self.assert_invalid(tmp, prior)

    def test_extra_case_name_raises(self):
        self.require()
        prior = self.valid_prior()
        extra = dict(prior["cases"][0], name="surprise_case")
        prior["cases"].append(extra)
        with tempfile.TemporaryDirectory() as tmp:
            self.assert_invalid(tmp, prior)

    def test_duplicate_case_name_raises(self):
        self.require()
        prior = self.valid_prior()
        prior["cases"].append(dict(prior["cases"][0]))
        with tempfile.TemporaryDirectory() as tmp:
            self.assert_invalid(tmp, prior)

    def test_missing_cases_list_raises(self):
        self.require()
        prior = self.valid_prior()
        prior.pop("cases")
        with tempfile.TemporaryDirectory() as tmp:
            self.assert_invalid(tmp, prior)

    def test_malformed_json_raises(self):
        self.require()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prior.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                nrd.load_previous(path)

    def test_malformed_case_blocks_raise(self):
        self.require()
        mutations = [
            lambda record: record["cli"].__setitem__("distinct", "2"),
            lambda record: record["python"].__setitem__("total", 1.5),
            lambda record: record["python"].pop("total"),
            lambda record: record.pop("cli"),
        ]
        for mutate in mutations:
            prior = self.valid_prior()
            mutate(prior["cases"][0])
            with tempfile.TemporaryDirectory() as tmp:
                self.assert_invalid(tmp, prior)

    def test_previous_composes_with_expect_unified_at_parse_time(self):
        self.require()
        # --previous must NOT live in the --expect-* mutually exclusive
        # group: Phase 9's re-run passes both flags together. An argparse
        # rejection would surface as a usage error before the binary check.
        with tempfile.TemporaryDirectory() as tmp:
            prior_path = self.write_prior(tmp, self.valid_prior())
            code, _, err = run_main(
                ["--expect-unified", "--previous", str(prior_path),
                 "--rustkmer", str(Path(tmp) / "absent-rustkmer"),
                 "--out", str(Path(tmp) / "out.json")])
            self.assertEqual(code, 2)
            self.assertIn("rustkmer binary not found", err)
            self.assertNotIn("not allowed with argument", err)


if __name__ == "__main__":
    unittest.main()