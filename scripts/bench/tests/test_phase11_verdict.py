#!/usr/bin/env python3
"""Unit suite for the Phase-12 verdict controller (scripts/bench/phase11.py).

Hand-built constants, no filesystem beyond tempdir, no measurement binaries
invoked: the verdict stage is a pure comparison of RECORDED medians and the
renderer is a pure transform of recorded documents, so this suite proves the
stage/exit-code contract, the verdict rule, the verdict-document key layout,
the defaults-only merge-arm argv, and the byte-identical renderer without a
real `/usr/bin/time` run.

The load-bearing rules encoded here (plan 12-01 Wave 0):
  * STAGES pins revalidate -> parity -> timed -> verdict -> render and the
    0/1/2 exit-code contract (infra -> 2, a measured NO publishes);
  * the verdict rule is match-or-beat `<=` per k, overall YES needs both k,
    and merge-t1 is scaling evidence excluded from YES/NO;
  * the verdict doc carries the pinned key layout plan 12-02's gates read;
  * merge_arm_argv is defaults-only by construction;
  * the renderer is mechanical — no measurement literals, no clock, and a
    re-render is byte-identical.

Stdlib unittest only — no pytest.
"""

import argparse
import collections
import contextlib
import copy
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.bench import phase11 as p11
from scripts.bench import merge_characterize as mc
from scripts.bench.prepare_inputs import write_manifest

# Fixture-only wall medians. They are asserted ABSENT from the controller
# source text (the renderer must carry no measurement literals).
MERGE_WALL = 21.25
JF_WALL = 63.5
T1_WALL = 88.125
FIXTURE_FLOATS = ("21.25", "63.5", "88.125")

RK_MERGE_OUT_SHA = "c" * 64
JF_MERGE_OUT_SHA = "d" * 64


def fake_provenance():
    """A structurally valid rustkmer provenance block (validate-clean)."""
    return {
        "binary": {"path": "/repo/target/release/rustkmer",
                   "size_bytes": 1234, "sha256": "a" * 64},
        "git_commit": "b" * 40,
        "git_dirty": False,
        "build_profile": "release",
        "rust_toolchain": "rustc 1.82.0 (fake)",
        "platform": "darwin-arm64",
        "created": "2026-11-17T00:00:00+00:00",
    }


def fake_jellyfish_provenance():
    """A structurally valid pinned-comparator provenance block."""
    prov = fake_provenance()
    prov["binary"] = {"path": "/opt/homebrew/Cellar/jellyfish/2.3.1/bin/"
                              "jellyfish",
                      "size_bytes": 374544, "sha256": "9" * 64}
    prov["build_profile"] = "pinned-comparator-2.3.1"
    return prov


def make_rep(wall, peak_rss=1000, cache_state="unavailable", round_index=0,
             arm_order=0):
    return {"wall_s": wall, "peak_rss_bytes": peak_rss,
            "cache_state": cache_state, "round": round_index,
            "arm_order": arm_order}


def make_arm(name, tool, threads, wall, unique=4000, total=12000,
             output_bytes=80000, output_sha256=None, provenance=None,
             command_line=None):
    """One merge arm with the recorded fields the stages/renderer consume."""
    if command_line is None:
        command_line = ["/bin/rustkmer", "merge", "-i",
                        "/inputs/part_001.k21.rkdb",
                        "/inputs/part_006.k21.rkdb",
                        "-o", "/scratch/merged.k21.rkdb"]
        if name == "merge-t1":
            command_line = command_line + ["--num-threads", "1"]
        elif name == "jellyfish-merge":
            command_line = ["jellyfish", "merge", "-o",
                            "/scratch/merged.k21.jf",
                            "/inputs/part_001.k21.jf",
                            "/inputs/part_006.k21.jf"]
    return {
        "name": name,
        "tool": tool,
        "threads": threads,
        "command_line": command_line,
        "reps": [make_rep(wall)],
        "medians": {"wall_s": wall, "peak_rss_bytes": 1000,
                    "peak_bytes": 1000, "cv_wall_pct": None,
                    "cv_warning": False},
        "unique_kmers": unique,
        "total_kmers": total,
        "output_bytes": output_bytes,
        "output_sha256": output_sha256 or (
            RK_MERGE_OUT_SHA if tool == "rustkmer" else JF_MERGE_OUT_SHA),
        "route": "not-reported",
        "provenance": provenance or fake_provenance(),
    }


def make_results_doc(merge_wall=MERGE_WALL, jf_wall=JF_WALL, t1_wall=T1_WALL,
                     k=21, unique=4000):
    """A schema-v1 merge results document (hand-built, phase 12)."""
    arms = [
        make_arm("merge", "rustkmer", None, merge_wall, unique=unique,
                 output_bytes=unique * 20),
    ]
    if t1_wall is not None:
        arms.append(make_arm("merge-t1", "rustkmer", 1, t1_wall,
                             unique=unique, output_bytes=unique * 20))
    arms.append(make_arm("jellyfish-merge", "jellyfish", None, jf_wall,
                         unique=unique,
                         output_bytes=unique * (10 if k == 21 else 12),
                         provenance=fake_jellyfish_provenance()))
    return {
        "schema_version": 1,
        "phase": 12,
        "session": "merge-timed",
        "params": {"k": k, "canonical": True, "reps": 3, "cooldown_s": 5.0},
        "platform": {"system": "Darwin", "release": "25.6.0",
                     "machine": "arm64", "python": "3.13.11"},
        "created": "2026-11-17T00:00:00+00:00",
        "input_fingerprint": [
            {"path": f"/inputs/part_001.k{k}.rkdb", "size_bytes": 10,
             "sha256": "1" * 64},
            {"path": f"/inputs/part_006.k{k}.rkdb", "size_bytes": 11,
             "sha256": "2" * 64},
        ],
        "arms": arms,
        "scratch": "/scratch/phase12",
        "provenance": fake_provenance(),
    }


def make_parity_doc(k=21, legs=None, anchors_exact=True, kind=None,
                    merges=None):
    """A phase12-merge-parity evidence document fixture."""
    return {
        "schema_version": 1,
        "kind": kind or p11.KIND_PARITY,
        "phase": 12,
        "k": k,
        "created": "2026-11-17T00:00:00+00:00",
        "legs_executed": list(legs) if legs is not None else list(
            p11.PARITY_LEGS),
        "anchors": {"expected": p11.UNION_TOTALS[k],
                    "actual": p11.UNION_TOTALS[k],
                    "exact": anchors_exact, "definition": "sum-of-counts"},
        "merges": merges if merges is not None else [
            {"tool": "rustkmer", "warmup": True},
            {"tool": "jellyfish", "warmup": True},
        ],
        "provenance": fake_provenance(),
    }


def make_ladder_doc():
    """A ladder-shaped fixture; the caveat is the harness's own constant."""
    caveat = mc.FULL_SCALE_CAVEAT
    return {
        "kind": "merge-characterization-ladder",
        "schema_version": 1,
        "summary": {
            "slopes": {
                "rustkmer_k21": {"linear": True,
                                 "slope_wall_s_per_entry": 6.67e-08,
                                 "ratio_40_over_10": 1.19},
                "rustkmer_k31": {"linear": True,
                                 "slope_wall_s_per_entry": 7.41e-08,
                                 "ratio_40_over_10": 1.37},
                "jellyfish_k21": {"linear": True,
                                  "slope_wall_s_per_entry": 8.97e-08,
                                  "ratio_40_over_10": 1.06},
                "jellyfish_k31": {"linear": True,
                                  "slope_wall_s_per_entry": 1.008e-07,
                                  "ratio_40_over_10": 1.18},
            },
            "extrapolated_full_scale": {
                "caveat": caveat,
                "full_scale_entries": {"21": 897266581, "31": 1146353600},
                "rustkmer_k21": {
                    "predicted_full_scale_wall_s": 53.84865958547661,
                    "method": "two-point linear (fixture)",
                    "flagged_nonlinear": False},
                "rustkmer_k31": {
                    "predicted_full_scale_wall_s": 73.36277547930045,
                    "method": "two-point linear (fixture)",
                    "flagged_nonlinear": False},
                "jellyfish_k21": {
                    "predicted_full_scale_wall_s": 77.26391787523114,
                    "method": "two-point linear (fixture)",
                    "flagged_nonlinear": False},
                "jellyfish_k31": {
                    "predicted_full_scale_wall_s": 105.52449658729188,
                    "method": "two-point linear (fixture)",
                    "flagged_nonlinear": False},
            },
        },
    }


def make_verdict_doc(results_docs):
    """A verdict doc fixture computed through the controller's own rule."""
    verdicts = [p11.verdict_block(doc["params"]["k"], doc)
                for doc in results_docs]
    overall = "YES" if all(v["result"] == "YES" for v in verdicts) else "NO"
    return {
        "schema_version": 1,
        "kind": p11.KIND_VERDICT,
        "phase": 12,
        "created": "2026-11-17T00:00:00+00:00",
        "overall": overall,
        "decision": "NO-INVEST" if overall == "YES" else "INVEST",
        "exit_code": 0 if overall == "YES" else 1,
        "rule": p11.VERDICT_RULE,
        "verdicts": verdicts,
        "inputs": [],
        "provenance": fake_provenance(),
    }


def make_manifest(k=21):
    """A revalidated-manifest-shaped fixture (the pinned part pair)."""
    return {
        "artifacts": [
            {"path": f"/inputs/part_001.k{k}.rkdb", "k": k,
             "sha256": "1" * 64, "size_bytes": 10},
            {"path": f"/inputs/part_006.k{k}.rkdb", "k": k,
             "sha256": "2" * 64, "size_bytes": 11},
        ],
        "jellyfish_inputs": [
            {"path": f"/inputs/part_001.k{k}.jf", "k": k,
             "sha256": "3" * 64, "hash_size": "1G"},
            {"path": f"/inputs/part_006.k{k}.jf", "k": k,
             "sha256": "4" * 64, "hash_size": "1G"},
        ],
    }


def write_json(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")


def render_docs(results=None, parity=None, verdict=None, ladder=None):
    return {
        "results": results if results is not None else
        [make_results_doc(k=21), make_results_doc(k=31)],
        "parity": parity if parity is not None else
        [make_parity_doc(k=21), make_parity_doc(k=31)],
        "verdict": verdict,
        "ladder": ladder if ladder is not None else make_ladder_doc(),
    }


class TempDirCase(unittest.TestCase):
    """mkdtemp setUp + rmtree cleanup."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)


class TestStageContract(TempDirCase):
    """The five-stage dispatch and the 0/1/2 exit-code contract."""

    def test_stages_and_exit_codes_pinned(self):
        """The stage order is pinned by construction (D-01)."""
        self.assertEqual(
            p11.STAGES,
            ("revalidate", "parity", "timed", "verdict", "render"))
        self.assertEqual((p11.EXIT_OK, p11.EXIT_NO, p11.EXIT_INVALID),
                         (0, 1, 2))
        self.assertEqual(p11.VERDICT_PREFIX, "PHASE11 VERDICT")
        self.assertEqual(p11.PHASE, 12)

    def test_unknown_stage_exits_two(self):
        """An unknown --stage value exits 2 (argparse choices)."""
        with self.assertRaises(SystemExit) as ctx:
            p11.main(["--stage", "bogus", "--out", str(self.tmp / "o.json")])
        self.assertEqual(ctx.exception.code, p11.EXIT_INVALID)

    def test_unimplemented_session_stage_exits_two_naming_it(self):
        """A stage plan 12-04 has not added yet exits 2 naming the stage."""
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), \
                self.assertRaises(SystemExit) as ctx:
            p11.main(["--stage", "revalidate",
                      "--out", str(self.tmp / "o.json")])
        self.assertEqual(ctx.exception.code, p11.EXIT_INVALID)
        self.assertIn("revalidate", stderr.getvalue())
        self.assertIn("not implemented", stderr.getvalue())

    def test_verdict_stage_requires_two_results_docs(self):
        """Missing results documents are exit 2, never a verdict."""
        with self.assertRaises(SystemExit) as ctx:
            p11.main(["--stage", "verdict",
                      "--out", str(self.tmp / "o.json")])
        self.assertEqual(ctx.exception.code, p11.EXIT_INVALID)

    def test_infra_failure_maps_to_exit_two_without_artifact(self):
        """A raise inside a stage maps to exit 2; no artifact is written.

        Run as a script so the module-level exception handler itself is
        what is under test: infra != verdict (Pitfall 10).
        """
        bad = self.tmp / "bad-results.json"
        write_json(bad, {"schema_version": 1, "phase": 12,
                         "session": "merge-timed", "arms": []})
        bad2 = self.tmp / "bad-results-k31.json"
        write_json(bad2, {"schema_version": 1, "phase": 12,
                          "session": "merge-timed", "arms": []})
        out = self.tmp / "verdict.json"
        proc = subprocess.run(
            [sys.executable, p11.__file__, "--stage", "verdict",
             "--results", str(bad), str(bad2), "--out", str(out)],
            capture_output=True, text=True, cwd=str(p11.REPO_ROOT))
        self.assertEqual(proc.returncode, p11.EXIT_INVALID)
        self.assertIn("phase11.py:", proc.stderr)
        self.assertIn("arms", proc.stderr)
        self.assertFalse(out.exists(),
                         "an infrastructure failure must write no artifact")

    def test_help_exits_zero_without_import_error(self):
        """The script-execution path fixup works end to end."""
        proc = subprocess.run(
            [sys.executable, p11.__file__, "--help"],
            capture_output=True, text=True, cwd=str(p11.REPO_ROOT))
        self.assertEqual(proc.returncode, 0)
        for bad in ("Traceback", "ImportError", "ModuleNotFoundError"):
            self.assertNotIn(bad, proc.stderr)


class TestVerdictRule(TempDirCase):
    """The match-or-beat rule, exit polarity, and the pinned key layout."""

    def verdict_run(self, doc21, doc31):
        d21 = self.tmp / "results-k21.json"
        d31 = self.tmp / "results-k31.json"
        out = self.tmp / "verdict.json"
        write_json(d21, doc21)
        write_json(d31, doc31)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = p11.main(["--stage", "verdict", "--results", str(d21),
                             str(d31), "--out", str(out)])
        return code, out, stdout.getvalue()

    def test_verdict_yes_at_both_k_returns_exit_ok_no_invest(self):
        """Merge matches-or-beats at both k -> exit 0, decision NO-INVEST."""
        code, out, printed = self.verdict_run(make_results_doc(k=21),
                                              make_results_doc(k=31))
        self.assertEqual(code, p11.EXIT_OK)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc["kind"], "phase11-merge-verdict")
        self.assertEqual(doc["overall"], "YES")
        self.assertEqual(doc["decision"], "NO-INVEST")
        self.assertEqual(doc["exit_code"], 0)
        self.assertTrue(printed.startswith("PHASE11 VERDICT k=21 result="))
        self.assertIn("overall=YES decision=NO-INVEST exit_code=0", printed)

    def test_measured_no_publishes_invest_with_exit_one(self):
        """Losing at k=31 only -> exit 1/INVEST, and the artifact publishes.

        Both per-k blocks are written: a measured NO is a valid recorded
        result, never an abort (exit codes are reserved for observations).
        """
        doc31 = make_results_doc(merge_wall=97.5, k=31)
        code, out, printed = self.verdict_run(make_results_doc(k=21), doc31)
        self.assertEqual(code, p11.EXIT_NO)
        self.assertTrue(out.exists(), "a measured NO publishes")
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc["decision"], "INVEST")
        self.assertEqual(doc["exit_code"], 1)
        self.assertEqual(doc["overall"], "NO")
        self.assertEqual(sorted(block["k"] for block in doc["verdicts"]),
                         [21, 31])
        self.assertIn("overall=NO decision=INVEST exit_code=1", printed)

    def test_exact_median_equality_is_match_or_beat(self):
        """merge wall == jellyfish wall at both k is YES (no tolerance)."""
        doc21 = make_results_doc(merge_wall=MERGE_WALL, jf_wall=MERGE_WALL,
                                 k=21)
        doc31 = make_results_doc(merge_wall=MERGE_WALL, jf_wall=MERGE_WALL,
                                 k=31)
        code, out, _printed = self.verdict_run(doc21, doc31)
        self.assertEqual(code, p11.EXIT_OK)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc["overall"], "YES")
        for block in doc["verdicts"]:
            self.assertEqual(block["result"], "YES")

    def test_merge_t1_excluded_from_verdict_but_recorded_as_scaling(self):
        """A slow t1 never changes the result; it lands under `scaling`."""
        baseline = p11.verdict_block(21, make_results_doc(k=21))
        with_slow_t1 = p11.verdict_block(21, make_results_doc(k=21))
        self.assertEqual(baseline["result"], with_slow_t1["result"])
        self.assertEqual(with_slow_t1["scaling"]["wall_s"], T1_WALL)
        self.assertEqual(with_slow_t1["scaling"]["arm"], "merge-t1")
        without_t1 = p11.verdict_block(
            21, make_results_doc(k=21, t1_wall=None))
        self.assertEqual(without_t1["result"], baseline["result"])
        self.assertIsNone(without_t1["scaling"])

    def test_verdict_doc_key_layout_pinned(self):
        """The exact key layout plan 12-02's gates consume, verbatim rule."""
        code, out, _printed = self.verdict_run(make_results_doc(k=21),
                                               make_results_doc(k=31))
        self.assertEqual(code, p11.EXIT_OK)
        doc = json.loads(out.read_text(encoding="utf-8"))
        for key in ("overall", "decision", "exit_code", "rule"):
            self.assertIn(key, doc)
        self.assertEqual(doc["rule"], p11.VERDICT_RULE)
        self.assertEqual(doc["kind"], p11.KIND_VERDICT)
        self.assertEqual(doc["phase"], 12)
        for block in doc["verdicts"]:
            for key in ("k", "result", "rustkmer_wall_s",
                        "jellyfish_wall_s"):
                self.assertIn(key, block)
            self.assertEqual(block["rule"], p11.VERDICT_RULE)
        # The recorded integers round-trip exactly; walls round-trip via
        # repr in the printed line.
        self.assertIsInstance(doc["verdicts"][0]["rustkmer_wall_s"], float)
        self.assertEqual(doc["inputs"][0]["path"],
                         str(self.tmp / "results-k21.json"))

    def test_verdict_block_rejects_mismatched_k_document(self):
        """A k=21 verdict against a k=31 document is a loud error."""
        with self.assertRaises(ValueError) as ctx:
            p11.verdict_block(21, make_results_doc(k=31))
        self.assertIn("mismatched", str(ctx.exception))

    def test_verdict_stage_rejects_duplicate_k_documents(self):
        """Two documents for the same k are exit 2, never a silent pick."""
        d21a = self.tmp / "a.json"
        d21b = self.tmp / "b.json"
        write_json(d21a, make_results_doc(k=21))
        write_json(d21b, make_results_doc(k=21))
        with self.assertRaises(SystemExit) as ctx:
            p11.main(["--stage", "verdict", "--results", str(d21a), str(d21b),
                      "--out", str(self.tmp / "o.json")])
        self.assertEqual(ctx.exception.code, p11.EXIT_INVALID)


class TestMergeArmArgv(unittest.TestCase):
    """Defaults-only argv by construction (MBENCH-01)."""

    def test_merge_arm_carries_no_num_threads(self):
        """The merge arm keeps the tool default: no --num-threads."""
        argv = p11.merge_arm_argv("merge", 21, make_manifest(),
                                  "/scratch/phase12", "/bin/rustkmer")
        self.assertNotIn("--num-threads", argv)
        self.assertEqual(argv[0], "/bin/rustkmer")
        self.assertEqual(argv[1], "merge")

    def test_merge_t1_carries_exactly_num_threads_one(self):
        """The like-for-like arm pins exactly [--num-threads, 1]."""
        argv = p11.merge_arm_argv("merge-t1", 21, make_manifest(),
                                  "/scratch/phase12", "/bin/rustkmer")
        self.assertEqual(
            argv[-2:], ["--num-threads", "1"])
        self.assertEqual(argv.count("--num-threads"), 1)

    def test_jellyfish_merge_argv_defaults_only_exact(self):
        """Defaults only — no flag copying between subcommands."""
        argv = p11.merge_arm_argv("jellyfish-merge", 21, make_manifest(),
                                  "/scratch/phase12", "/bin/rustkmer")
        self.assertEqual(argv, ["jellyfish", "merge", "-o",
                                "/scratch/phase12/merged.k21.jf",
                                "/inputs/part_001.k21.jf",
                                "/inputs/part_006.k21.jf"])

    def test_arm_argv_resolved_from_manifest_records(self):
        """Inputs come from the manifest records, never re-derived paths."""
        manifest = make_manifest(k=31)
        argv = p11.merge_arm_argv("merge", 31, manifest, "/scratch/phase12",
                                  "/bin/rustkmer")
        self.assertIn("/inputs/part_001.k31.rkdb", argv)
        self.assertIn("/inputs/part_006.k31.rkdb", argv)
        self.assertIn("/scratch/phase12/merged.k31.rkdb", argv)

    def test_arm_argv_rejects_drifted_manifest_and_unknown_arm(self):
        """A drifted manifest or an unknown arm name is a loud error."""
        with self.assertRaises(ValueError) as ctx:
            p11.merge_arm_argv("merge", 21, {"artifacts": []},
                               "/scratch/phase12", "/bin/rustkmer")
        self.assertIn("drifted", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            p11.merge_arm_argv("count", 21, make_manifest(),
                               "/scratch/phase12", "/bin/rustkmer")
        self.assertIn("unknown arm", str(ctx.exception))


class TestValidateDocs(TempDirCase):
    """Invalid documents never reach disk / are never consumed."""

    def test_parity_document_rejects_wrong_kind(self):
        """A foreign kind is rejected loudly (never merged across kinds)."""
        doc = make_parity_doc(kind=p11.KIND_ROUND0)
        with self.assertRaises(ValueError) as ctx:
            p11._validate_parity_document(doc)
        self.assertIn("kind", str(ctx.exception))

    def test_parity_document_rejects_missing_legs(self):
        """Aggregate-only parity is never accepted (PARITY-GATE.md §4)."""
        doc = make_parity_doc(legs=["leg1-aggregate-conservation",
                                    "leg3-dump-vs-dump"])
        with self.assertRaises(ValueError) as ctx:
            p11._validate_parity_document(doc)
        self.assertIn("leg2-recount-vs-merged", str(ctx.exception))

    def test_parity_document_rejects_anchor_mismatch_and_empty_merges(self):
        """anchors.exact=false or no merge records is invalid."""
        with self.assertRaises(ValueError) as ctx:
            p11._validate_parity_document(make_parity_doc(anchors_exact=False))
        self.assertIn("anchors", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            p11._validate_parity_document(make_parity_doc(merges=[]))
        self.assertIn("merge records", str(ctx.exception))

    def test_results_document_rejects_schema_failure(self):
        """A doc failing bench.validate_schema is rejected (schema v1)."""
        doc = make_results_doc()
        doc["arms"] = [{"name": "merge"}]
        with self.assertRaises(ValueError):
            p11._validate_results_document(doc)

    def test_results_document_rejects_foreign_phase_and_evidence_kind(self):
        """Foreign phases and evidence kinds are never consumed as results."""
        doc = make_results_doc()
        doc["phase"] = 10
        with self.assertRaises(ValueError) as ctx:
            p11._validate_results_document(doc)
        self.assertIn("phase", str(ctx.exception))
        doc = make_results_doc()
        doc["kind"] = p11.KIND_PARITY
        with self.assertRaises(ValueError) as ctx:
            p11._validate_results_document(doc)
        self.assertIn("evidence kind", str(ctx.exception))

    def test_results_document_rejects_non_merge_arm_names(self):
        """A count-era document is rejected: only merge arms ride here."""
        doc = make_results_doc()
        doc["arms"][0]["name"] = "rustkmer-count-A"
        with self.assertRaises(ValueError) as ctx:
            p11._validate_results_document(doc)
        self.assertIn("merge arms", str(ctx.exception))


class TestRenderSections(TempDirCase):
    """Every MBENCH-04 section, all read from recorded documents."""

    def render(self, docs):
        return p11.render_report_text(docs)

    def test_asymmetry_sentence_and_ladder_caveat_verbatim(self):
        """The pre-agreed sentence and the caveat appear verbatim."""
        text = self.render(render_docs(verdict=make_verdict_doc(
            render_docs()["results"])))
        self.assertIn(p11.ASYMMETRY_SENTENCE, text)
        self.assertIn(mc.FULL_SCALE_CAVEAT, text)

    def test_methodology_rows_carry_threads_flags_route_sha256(self):
        """Per-arm rows disclose threads/flags/route/output+binary sha256."""
        docs = render_docs(verdict=make_verdict_doc(render_docs()["results"]))
        text = self.render(docs)
        self.assertIn("threads", text)
        self.assertIn("route", text)
        self.assertIn(RK_MERGE_OUT_SHA, text)
        self.assertIn(JF_MERGE_OUT_SHA, text)
        self.assertIn("not-reported", text)
        self.assertIn("--num-threads 1", text)
        self.assertIn("defaults", text)

    def test_entry_rate_and_byte_rate_rows_from_recorded_values(self):
        """Rates are computed ONLY from recorded distinct/bytes/walls."""
        docs = render_docs(verdict=make_verdict_doc(render_docs()["results"]))
        text = self.render(docs)
        arm = docs["results"][0]["arms"][0]
        entry_rate = arm["unique_kmers"] / arm["medians"]["wall_s"]
        byte_rate = arm["output_bytes"] / arm["medians"]["wall_s"]
        self.assertIn(repr(entry_rate), text)
        self.assertIn(repr(byte_rate), text)
        self.assertIn("output B/entry", text)

    def test_t1_pool_contract_and_rss_context_framing_present(self):
        """The t1 row carries the 2-OS-thread pool contract; RSS is context."""
        docs = render_docs(verdict=make_verdict_doc(render_docs()["results"]))
        text = self.render(docs)
        self.assertIn(p11.T1_POOL_CONTRACT, text)
        self.assertIn(p11.RSS_CONTEXT_FRAMING, text)
        self.assertIn("never enters the", text)

    def test_predicted_vs_measured_reads_ladder_values(self):
        """The table reads summary.slopes/extrapolated_full_scale values."""
        docs = render_docs(verdict=make_verdict_doc(render_docs()["results"]))
        ladder = docs["ladder"]["summary"]["extrapolated_full_scale"]
        text = self.render(docs)
        for key in ("rustkmer_k21", "rustkmer_k31", "jellyfish_k21",
                    "jellyfish_k31"):
            predicted = ladder[key]["predicted_full_scale_wall_s"]
            self.assertIn(repr(predicted), text)
        self.assertIn("Predicted vs measured", text)

    def test_render_rejects_inconsistent_verdict_document(self):
        """The verdict doc must match the results docs it labels."""
        docs = render_docs()
        other = make_verdict_doc([make_results_doc(k=21),
                                  make_results_doc(merge_wall=97.5, k=31)])
        docs["verdict"] = other
        with self.assertRaises(ValueError) as ctx:
            self.render(docs)
        self.assertIn("inconsistent evidence", str(ctx.exception))

    def test_render_rejects_ladder_caveat_mismatch(self):
        """A ladder doc not written by this harness is refused."""
        docs = render_docs(verdict=make_verdict_doc(render_docs()["results"]))
        docs["ladder"]["summary"]["extrapolated_full_scale"]["caveat"] = \
            "hand-edited caveat"
        with self.assertRaises(ValueError) as ctx:
            self.render(docs)
        self.assertIn("FULL_SCALE_CAVEAT", str(ctx.exception))


class TestRenderDeterminism(TempDirCase):
    """Byte-identical re-render; no clock fields; no measurement literals."""

    def full_docs(self):
        results = [make_results_doc(k=21), make_results_doc(k=31)]
        docs = render_docs(results=results, verdict=make_verdict_doc(results))
        return docs

    def test_render_twice_byte_identical_without_created_field(self):
        """Re-render is byte-identical and the report has no clock field."""
        first = p11.render_report_text(self.full_docs())
        second = p11.render_report_text(copy.deepcopy(self.full_docs()))
        self.assertEqual(first, second)
        self.assertNotIn("created", first)
        self.assertNotIn("timestamp", first)
        self.assertTrue(first.endswith("\n"))

    def test_changing_a_median_changes_the_rendered_row(self):
        """The renderer reads values — no literals (T-12-01)."""
        results = [make_results_doc(k=21),
                   make_results_doc(merge_wall=30.75, k=31)]
        changed = p11.render_report_text(
            render_docs(results=results, verdict=make_verdict_doc(results)))
        self.assertIn(repr(30.75), changed)
        baseline = p11.render_report_text(self.full_docs())
        self.assertNotEqual(baseline, changed)

    def test_render_stage_end_to_end_publishes_report_and_proof(self):
        """--stage render writes both artifacts with a byte-identity proof."""
        docs = self.full_docs()
        paths = {}
        for name, doc in (("r21", docs["results"][0]),
                          ("r31", docs["results"][1]),
                          ("p21", docs["parity"][0]),
                          ("p31", docs["parity"][1]),
                          ("v", docs["verdict"]),
                          ("l", docs["ladder"])):
            path = self.tmp / f"{name}.json"
            write_json(path, doc)
            paths[name] = str(path)
        report = self.tmp / "12-MERGE-REPORT.md"
        proof = self.tmp / "12-RENDER-PROOF.json"
        code = p11.main([
            "--stage", "render",
            "--results", paths["r21"], paths["r31"],
            "--parity-doc", paths["p21"], paths["p31"],
            "--verdict-doc", paths["v"], "--ladder-doc", paths["l"],
            "--out", str(report), "--proof-out", str(proof)])
        self.assertEqual(code, p11.EXIT_OK)
        self.assertTrue(report.exists())
        proof_doc = json.loads(proof.read_text(encoding="utf-8"))
        self.assertEqual(proof_doc["kind"], p11.KIND_RENDER_PROOF)
        self.assertTrue(proof_doc["byte_identical"])
        self.assertEqual(proof_doc["first_render_sha256"],
                         proof_doc["second_render_sha256"])
        self.assertIn("renderer_commit", proof_doc)

    def test_render_stage_requires_all_inputs(self):
        """Missing render inputs are exit 2, never a partial publish."""
        with self.assertRaises(SystemExit) as ctx:
            p11.main(["--stage", "render",
                      "--results", str(self.tmp / "r21.json"),
                      str(self.tmp / "r31.json"),
                      "--out", str(self.tmp / "report.md")])
        self.assertEqual(ctx.exception.code, p11.EXIT_INVALID)

    def test_source_hygiene_no_inprocess_normalizer_no_shell_no_literals(self):
        """WR-01/T-12-03 gates plus the no-fixture-literals gate."""
        source = Path(p11.__file__).read_text(encoding="utf-8")
        # The in-process dump normalizer must never be referenced (WR-01).
        self.assertNotIn("normalize_dump_lines", source)
        # The in-process comparator must never be referenced; only the
        # streaming form (dump_vs_dump_equal_streaming) may appear.
        self.assertIsNone(re.search(r"dump_vs_dump_equal\b", source))
        # No shell strings anywhere (T-12-03).
        self.assertNotIn("shell=True", source)
        # The renderer carries no fixture measurement literals.
        for literal in FIXTURE_FLOATS:
            self.assertNotIn(literal, source)


# ---------------------------------------------------------------------------
# Plan 12-04 session stages: round-0 revalidate + parity (Leg-2 recount diff)
# ---------------------------------------------------------------------------

# 11-PREPARE-RECORD.md §3 recorded per-part values — fixtures use the REAL
# recorded integers so the anchor arithmetic exercises the true scale.
PART_TOTALS = {
    21: {"part_001": 4_483_548_820, "part_006": 4_483_550_383},
    31: {"part_001": 4_137_846_285, "part_006": 4_137_847_745},
}
PART_DISTINCT = {
    21: {"part_001": 664_641_739, "part_006": 664_724_158},
    31: {"part_001": 590_112_236, "part_006": 590_173_812},
}


def fake_identity_provenance(tool="rustkmer"):
    """A validate-clean provenance block carrying the PINNED binary hashes.

    assert_binary_identity compares sha256s against the ladder constants, so
    the happy-path fake must present the real pinned hashes to pass.
    """
    prov = fake_provenance()
    if tool == "rustkmer":
        prov["binary"] = {"path": "/repo/target/release/rustkmer",
                          "size_bytes": 1234,
                          "sha256": p11.RUSTKMER_BIN_SHA256}
    else:
        prov = fake_jellyfish_provenance()
        prov["binary"]["sha256"] = p11.JELLYFISH_BIN_SHA256
    return prov


def make_full_manifest(source_fingerprints=None):
    """Both-k manifest shaped like the recorded one (all 8 records)."""
    artifacts = []
    jellyfish_inputs = []
    for k in (21, 31):
        for part in ("part_001", "part_006"):
            artifacts.append({
                "path": f"/inputs/{part}.k{k}.rkdb", "k": k,
                "sha256": f"{k}{part[-1]}".ljust(64, "0"),
                "size_bytes": 10 + k, "tool": "rustkmer",
                "canonical": True,
                "distinct": PART_DISTINCT[k][part],
                "total": PART_TOTALS[k][part],
            })
            jellyfish_inputs.append({
                "path": f"/inputs/{part}.k{k}.jf", "k": k,
                "sha256": f"jf{k}{part[-1]}".ljust(64, "0"),
                "size_bytes": 5 + k, "hash_size": "1G",
            })
    manifest = {
        "kind": "merge-input-manifest", "schema_version": 1,
        "artifacts": artifacts, "jellyfish_inputs": jellyfish_inputs,
        "source_fingerprints": (source_fingerprints
                                if source_fingerprints is not None else
                                [{"path": str(p11.PART_PATHS[name]),
                                  "sha256": "s" * 64, "size_bytes": 100}
                                 for name in sorted(p11.PART_PATHS)]),
    }
    return manifest


def fixture_revalidate(artifacts_dir):
    """The revalidate contract over a tempdir fixture (identity-only).

    Mirrors prepare_inputs.revalidate_stage's loud identity contract —
    fingerprint every recorded artifact, reject drift, reject unrecorded
    .rkdb/.jf files — without the binary-bound stats() re-check (that leg is
    live-proven in test_prepare_inputs.py against the real artifacts).
    """
    artifacts_dir = Path(artifacts_dir)
    manifest = json.loads(
        (artifacts_dir / "manifest.json").read_text(encoding="utf-8"))
    recorded_names = set()
    for record in (manifest.get("artifacts", [])
                   + manifest.get("jellyfish_inputs", [])):
        path = Path(record["path"])
        if not path.is_file():
            raise RuntimeError(
                f"revalidate: recorded artifact missing: {path}")
        fp = p11.fingerprint(path)
        if fp["sha256"] != record["sha256"]:
            raise RuntimeError(
                f"revalidate: {path.name} sha256 {fp['sha256']} != recorded "
                f"{record['sha256']} — tampered or rebuilt artifact, never a "
                "silent repair")
        recorded_names.add(path.name)
    for path in sorted(artifacts_dir.iterdir()):
        if (path.is_file() and path.suffix in (".rkdb", ".jf")
                and path.name not in recorded_names):
            raise RuntimeError(
                f"revalidate: artifact {path.name} has no manifest record — "
                "an unrecorded artifact is a loud error, never a silent "
                "rebuild (probe MBENCH-01/empty)")
    return manifest


class TestAnchorEquality(unittest.TestCase):
    """EXACT union-anchor equality over the manifest's per-part records."""

    def test_exact_per_part_sums_pass_and_carry_layout(self):
        """Real per-part Totals sum to the union anchors; layout is pinned."""
        anchors = p11.assert_anchor_equality(make_full_manifest())
        self.assertEqual(anchors["21"],
                         {"sum": 8_967_099_203, "expected": 8_967_099_203,
                          "exact": True})
        self.assertEqual(anchors["31"],
                         {"sum": 8_275_694_030, "expected": 8_275_694_030,
                          "exact": True})

    def test_one_off_sum_raises_naming_both_values(self):
        """A one-off per-part total is a loud error naming computed/expected."""
        manifest = make_full_manifest()
        manifest["artifacts"][0]["total"] += 1
        with self.assertRaises(RuntimeError) as ctx:
            p11.assert_anchor_equality(manifest)
        message = str(ctx.exception)
        self.assertIn(str(8_967_099_203 + 1), message)
        self.assertIn(str(8_967_099_203), message)
        self.assertIn("sum-of-counts", message)

    def test_missing_k_records_raise(self):
        """A manifest missing one k's records cannot reconcile its anchor."""
        manifest = make_full_manifest()
        manifest["artifacts"] = [record for record in manifest["artifacts"]
                                 if record["k"] != 31]
        with self.assertRaises(RuntimeError) as ctx:
            p11.assert_anchor_equality(manifest)
        self.assertIn("k=31", str(ctx.exception))


class TestSessionBudget(unittest.TestCase):
    """D-12 session-budget arithmetic (deterministic, constants cited)."""

    def test_recorded_inputs_exceed_floor_and_deterministic(self):
        """The recorded inputs yield a GiB int above the derived floor."""
        budget = p11.session_budget_gb(
            inputs_bytes=93_135_484_166,
            entries={"21": 897266581, "31": 1146353600})
        self.assertIsInstance(budget, int)
        self.assertGreater(budget, p11.DEFAULT_DISK_FLOOR_GB)
        self.assertEqual(
            budget, p11.session_budget_gb(
                inputs_bytes=93_135_484_166,
                entries={"21": 897266581, "31": 1146353600}))

    def test_breakdown_cites_constants_and_terms(self):
        """The breakdown names DUMP_BYTES_PER_LINE and the ladder source."""
        breakdown = p11.session_budget(
            inputs_bytes=93_135_484_166,
            entries={"21": 897266581, "31": 1146353600})
        constants = breakdown["constants"]
        self.assertEqual(constants["dump_bytes_per_line"],
                         p11.DUMP_BYTES_PER_LINE)
        self.assertIn("11-LADDER-RESULTS.json", constants["entries_source"])
        # The terms recompute exactly from the pinned formula.
        gib = 1 << 30
        self.assertEqual(breakdown["parity_transient_gb"],
                         {"21": -(-897266581 * 30 * 3 // gib),
                          "31": -(-1146353600 * 30 * 3 // gib)})
        self.assertEqual(breakdown["timed_transient_gb"],
                         -(-1146353600 * 20 // gib))
        self.assertEqual(breakdown["session_budget_gb"],
                         breakdown["inputs_gb"]
                         + sum(breakdown["parity_transient_gb"].values())
                         + breakdown["timed_transient_gb"])


class TestRecountVsMergedEqual(TempDirCase):
    """Leg-2 recount-vs-merged diff through the streaming dump pipeline."""

    def write_dump(self, name, lines):
        path = self.tmp / name
        path.write_text("".join(line + "\n" for line in lines),
                        encoding="utf-8")
        return path

    def builders(self, recount_lines, merged_lines):
        """cp-style builders: each receives the raw output path argument and
        writes the fixture bytes there itself (the via_stdout=False shape —
        rustkmer dump -o writes its own file, nothing is captured)."""
        recount_fixture = self.write_dump("recount.txt", recount_lines)
        merged_fixture = self.write_dump("merged.txt", merged_lines)
        received = []
        recount_builder = lambda raw: (received.append(("recount", raw)),
                                       ["cp", str(recount_fixture),
                                        str(raw)])[-1]
        merged_builder = lambda raw: (received.append(("merged", raw)),
                                      ["cp", str(merged_fixture),
                                       str(raw)])[-1]
        return recount_builder, merged_builder, received

    def test_identical_unordered_fixtures_pass_deterministically(self):
        """GREEN: identical fixtures pass; unordered lines sort LC_ALL=C."""
        lines = ["CCCC\t1", "AAAA\t2", "GGGG\t5", "TTTT\t3"]
        recount_builder, merged_builder, received = self.builders(lines,
                                                                  lines)
        self.assertTrue(p11.recount_vs_merged_equal(
            "unused.rkdb", "unused.rkdb", "unused",
            workdir=self.tmp / "leg2",
            recount_dump_builder=recount_builder,
            merged_dump_builder=merged_builder))
        # The builders received a raw output path argument each (the
        # via_stdout=False contract: the dump command writes its own file).
        self.assertEqual([name for name, _raw in received],
                         ["recount", "merged"])
        for _name, raw in received:
            self.assertTrue(str(raw).endswith(".raw"))

    def test_reordered_identical_lines_pass(self):
        """GREEN: byte order across the two sides does not matter."""
        recount_builder, merged_builder, _received = self.builders(
            ["AAAA\t2", "CCCC\t1"], ["CCCC\t1", "AAAA\t2"])
        self.assertTrue(p11.recount_vs_merged_equal(
            "unused.rkdb", "unused.rkdb", "unused",
            workdir=self.tmp / "leg2",
            recount_dump_builder=recount_builder,
            merged_dump_builder=merged_builder))

    def test_altered_count_raises_naming_line_and_sides(self):
        """RED: one differing count names the sorted line and both sides."""
        recount_builder, merged_builder, _received = self.builders(
            ["AAAA\t2", "CCCC\t2"], ["AAAA\t2", "CCCC\t1"])
        with self.assertRaises(RuntimeError) as ctx:
            p11.recount_vs_merged_equal(
                "unused.rkdb", "unused.rkdb", "unused",
                workdir=self.tmp / "leg2",
                recount_dump_builder=recount_builder,
                merged_dump_builder=merged_builder)
        message = str(ctx.exception)
        self.assertIn("line 1", message)
        self.assertIn("recount", message)
        self.assertIn("merged", message)
        self.assertIn("CCCC\\t2", message)
        self.assertIn("CCCC\\t1", message)

    def test_empty_side_raises_loudly(self):
        """RED: an empty dump can never pass the gate (MBENCH-02/empty)."""
        recount_builder, merged_builder, _received = self.builders(
            ["AAAA\t1"], [])
        with self.assertRaises(RuntimeError) as ctx:
            p11.recount_vs_merged_equal(
                "unused.rkdb", "unused.rkdb", "unused",
                workdir=self.tmp / "leg2",
                recount_dump_builder=recount_builder,
                merged_dump_builder=merged_builder)
        self.assertIn("empty", str(ctx.exception))

    def test_length_mismatch_raises(self):
        """RED: differing line counts name the length mismatch."""
        recount_builder, merged_builder, _received = self.builders(
            ["AAAA\t1", "CCCC\t1"], ["AAAA\t1"])
        with self.assertRaises(RuntimeError) as ctx:
            p11.recount_vs_merged_equal(
                "unused.rkdb", "unused.rkdb", "unused",
                workdir=self.tmp / "leg2",
                recount_dump_builder=recount_builder,
                merged_dump_builder=merged_builder)
        self.assertIn("length", str(ctx.exception))
        self.assertIn("2 lines", str(ctx.exception))
        self.assertIn("1 lines", str(ctx.exception))

    def test_malformed_line_raises(self):
        """RED: a non 'kmer count' line is a loud parse error."""
        recount_builder, merged_builder, _received = self.builders(
            ["AAAA\t1"], ["AAAA\t1", "garbage"])
        with self.assertRaises(RuntimeError) as ctx:
            p11.recount_vs_merged_equal(
                "unused.rkdb", "unused.rkdb", "unused",
                workdir=self.tmp / "leg2",
                recount_dump_builder=recount_builder,
                merged_dump_builder=merged_builder)
        self.assertIn("dump parse", str(ctx.exception))

    def test_stdout_only_builder_cannot_pass(self):
        """RED: Leg 2 is via_stdout=False — stdout is never captured into
        the raw dump file, so a stdout-only dump builder cannot pass."""
        stdout_fixture = self.write_dump("stdout.txt", ["AAAA\t1"])
        recount_builder = lambda raw: ["cat", str(stdout_fixture)]
        merged_fixture = self.write_dump("merged.txt", ["AAAA\t1"])
        merged_builder = lambda raw: ["cp", str(merged_fixture), str(raw)]
        with self.assertRaises(RuntimeError):
            p11.recount_vs_merged_equal(
                "unused.rkdb", "unused.rkdb", "unused",
                workdir=self.tmp / "leg2",
                recount_dump_builder=recount_builder,
                merged_dump_builder=merged_builder)


class TestSourceFingerprintCrossCheck(TempDirCase):
    """Source-swap defense: re-fingerprint the pinned part pair."""

    def write_sources(self):
        paths = {}
        for name, seed in (("part_001", "src-a"), ("part_006", "src-b")):
            path = self.tmp / f"{name}.fq.gz"
            path.write_text(seed, encoding="utf-8")
            paths[name] = path
        return paths

    def recorded_fingerprints(self, paths):
        return [{"path": str(paths[name]),
                 "sha256": p11.fingerprint(paths[name])["sha256"],
                 "size_bytes": p11.fingerprint(paths[name])["size_bytes"]}
                for name in sorted(paths)]

    def test_matching_sources_pass(self):
        """GREEN: re-fingerprinted sources match the manifest records."""
        paths = self.write_sources()
        manifest = make_full_manifest(
            source_fingerprints=self.recorded_fingerprints(paths))
        fps = p11.check_source_fingerprints(manifest, source_paths=paths)
        self.assertEqual(len(fps), 2)
        self.assertEqual({Path(fp["path"]).name for fp in fps},
                         {"part_001", "part_006"})

    def test_swapped_source_raises_naming_both_hashes(self):
        """RED: a regenerated source names recorded vs computed hashes."""
        paths = self.write_sources()
        manifest = make_full_manifest(
            source_fingerprints=self.recorded_fingerprints(paths))
        paths["part_006"].write_text("swapped bytes", encoding="utf-8")
        with self.assertRaises(RuntimeError) as ctx:
            p11.check_source_fingerprints(manifest, source_paths=paths)
        message = str(ctx.exception)
        self.assertIn("part_006", message)
        self.assertIn(p11.fingerprint(paths["part_006"])["sha256"], message)
        self.assertIn("s" * 64, message)

    def test_missing_record_raises_naming_the_part(self):
        """RED: a manifest without a part's source record is a loud error."""
        paths = self.write_sources()
        manifest = make_full_manifest(source_fingerprints=[])
        with self.assertRaises(RuntimeError) as ctx:
            p11.check_source_fingerprints(manifest, source_paths=paths)
        self.assertIn("part_001", str(ctx.exception))


class TestRound0DocBuilder(unittest.TestCase):
    """The round-0 evidence layout plan 12-02's gates consume."""

    def test_anchors_keyed_by_string_k_with_pinned_fields(self):
        """anchors is keyed '21'/'31', each carrying {sum, expected, exact}."""
        manifest = make_full_manifest()
        anchors = p11.assert_anchor_equality(manifest)
        doc = p11.round0_doc(
            manifest_digest={"path": "/inputs/manifest.json",
                             "sha256": "m" * 64, "size_bytes": 10},
            anchors=anchors,
            budget=p11.session_budget(inputs_bytes=93_135_484_166),
            df_sample={"path": "/scratch", "total": 1, "used": 0, "free": 1},
            binary_identity={"rustkmer": {"sha256": "r" * 64},
                             "jellyfish": {"sha256": "j" * 64}},
            source_fingerprints=[],
            provenance=fake_provenance(),
            artifacts_dir="/inputs")
        self.assertEqual(doc["kind"], p11.KIND_ROUND0)
        self.assertEqual(sorted(doc["anchors"]), ["21", "31"])
        for k_str, entry in doc["anchors"].items():
            self.assertEqual(sorted(entry), ["exact", "expected", "sum"])
            self.assertTrue(entry["exact"])
            self.assertEqual(entry["expected"], p11.UNION_TOTALS[int(k_str)])
        self.assertIn("session_budget_gb", doc["session_budget"])
        self.assertIn("df_sample", doc)
        self.assertIn("binary_identity", doc)
        p11.validate_provenance(doc)

    def test_doc_builder_carries_manifest_digest(self):
        """The manifest digest rides the doc (re-hash provenance)."""
        manifest = make_full_manifest()
        doc = p11.round0_doc(
            manifest_digest={"path": "/inputs/manifest.json",
                             "sha256": "m" * 64, "size_bytes": 10},
            anchors=p11.assert_anchor_equality(manifest),
            budget=p11.session_budget(inputs_bytes=1),
            df_sample={"path": "/scratch", "total": 1, "used": 0, "free": 1},
            binary_identity={"rustkmer": {}, "jellyfish": {}},
            source_fingerprints=[{"path": "/src", "sha256": "s" * 64,
                                  "size_bytes": 1}],
            provenance=fake_provenance(),
            artifacts_dir="/inputs")
        self.assertEqual(doc["manifest_digest"]["sha256"], "m" * 64)


class TestRunRevalidateStage(TempDirCase):
    """run_revalidate: loud drift, unrecorded artifacts, pinned doc layout."""

    def write_stage_sources(self):
        paths = {}
        for name, seed in (("part_001", "src-a"), ("part_006", "src-b")):
            path = self.tmp / f"source-{name}"
            path.write_text(seed, encoding="utf-8")
            paths[name] = path
        return paths

    def build_fixture_artifacts(self, flip=None, stray=False):
        """A real tempdir artifacts dir with tiny recorded artifact files.

        All 8 fixture artifacts are written and fingerprinted FIRST; the
        `flip` target is tampered AFTER its fingerprint was recorded so the
        recorded sha256 no longer matches the on-disk bytes (drift).
        """
        sources = self.write_stage_sources()
        artifacts_dir = self.tmp / "artifacts"
        artifacts_dir.mkdir()
        manifest = make_full_manifest()
        for record in manifest["artifacts"]:
            path = artifacts_dir / Path(record["path"]).name
            path.write_text(f"bytes-{record['k']}-"
                            f"{Path(record['path']).stem}",
                            encoding="utf-8")
            fp = p11.fingerprint(path)
            record["path"] = str(path)
            record["sha256"], record["size_bytes"] = (
                fp["sha256"], fp["size_bytes"])
        for record in manifest["jellyfish_inputs"]:
            path = artifacts_dir / Path(record["path"]).name
            path.write_text(f"jf-{record['k']}-{Path(record['path']).stem}",
                            encoding="utf-8")
            fp = p11.fingerprint(path)
            record["path"] = str(path)
            record["sha256"], record["size_bytes"] = (
                fp["sha256"], fp["size_bytes"])
        manifest["source_fingerprints"] = [
            {"path": str(sources[name]),
             "sha256": p11.fingerprint(sources[name])["sha256"],
             "size_bytes": p11.fingerprint(sources[name])["size_bytes"]}
            for name in sorted(sources)]
        write_manifest(artifacts_dir / "manifest.json", manifest)
        if stray:
            (artifacts_dir / "stray.rkdb").write_text("stray",
                                                      encoding="utf-8")
        if flip:
            target = artifacts_dir / flip
            target.write_text("tampered-bytes", encoding="utf-8")
        return artifacts_dir, sources

    def stage_args(self, out):
        return argparse.Namespace(out=str(out), k=21, reps=3,
                                  cooldown_s=5.0, scratch=str(self.tmp),
                                  disk_floor_override=False)

    def run_stage(self, args, artifacts_dir, sources):
        usage = collections.namedtuple("usage", "total used free")
        fake_df = lambda path: usage(1 << 42, 0, 1 << 40)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = p11.run_revalidate(
                args, revalidate_fn=fixture_revalidate,
                provenance_fn=fake_identity_provenance,
                source_paths=sources, disk_fn=lambda *a, **k: 1 << 40,
                df_fn=fake_df, manifest_path=Path(artifacts_dir)
                / "manifest.json")
        return code, stdout.getvalue()

    def test_happy_path_writes_round0_doc_with_pinned_layout(self):
        """GREEN: anchors keyed '21'/'31', budget, df sample, digest."""
        artifacts_dir, sources = self.build_fixture_artifacts()
        out = self.tmp / "12-REVALIDATE.json"
        code, printed = self.run_stage(self.stage_args(out), artifacts_dir,
                                       sources)
        self.assertEqual(code, p11.EXIT_OK)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc["kind"], p11.KIND_ROUND0)
        self.assertEqual(sorted(doc["anchors"]), ["21", "31"])
        for k_str, entry in doc["anchors"].items():
            self.assertEqual(entry["sum"], entry["expected"])
            self.assertTrue(entry["exact"])
        self.assertGreater(doc["session_budget"]["session_budget_gb"],
                           p11.DEFAULT_DISK_FLOOR_GB)
        self.assertIn("free", doc["df_sample"])
        self.assertIn("manifest_digest", doc)
        self.assertEqual(len(doc["source_fingerprints"]), 2)

    def test_drifted_artifact_raises_naming_the_record(self):
        """RED: flipped artifact bytes are loud, never silent."""
        artifacts_dir, sources = self.build_fixture_artifacts(
            flip="part_001.k21.rkdb")
        with self.assertRaises(RuntimeError) as ctx:
            self.run_stage(self.stage_args(self.tmp / "o.json"),
                           artifacts_dir, sources)
        message = str(ctx.exception)
        self.assertIn("part_001.k21.rkdb", message)
        self.assertIn("sha256", message)
        self.assertIn("tampered", message)

    def test_unrecorded_stray_rkdb_raises(self):
        """RED: a stray .rkdb without a manifest record is a loud error."""
        artifacts_dir, sources = self.build_fixture_artifacts(stray=True)
        with self.assertRaises(RuntimeError) as ctx:
            self.run_stage(self.stage_args(self.tmp / "o.json"),
                           artifacts_dir, sources)
        self.assertIn("stray.rkdb", str(ctx.exception))

    def test_no_artifact_written_on_drift(self):
        """A failed round-0 gate writes no evidence doc."""
        artifacts_dir, sources = self.build_fixture_artifacts(
            flip="part_006.k31.rkdb")
        out = self.tmp / "12-REVALIDATE.json"
        with self.assertRaises(RuntimeError):
            self.run_stage(self.stage_args(out), artifacts_dir, sources)
        self.assertFalse(out.exists())


class TestBinaryIdentityTripwire(unittest.TestCase):
    """The binary-identity tripwire names recorded and expected hashes."""

    def test_wrong_sha256_raises_naming_both(self):
        """A rebuilt binary is a loud error, never a silent rebuild."""
        def drifted_provenance(executable, profile):
            prov = fake_identity_provenance("rustkmer")
            prov["binary"]["sha256"] = "f" * 64
            return prov
        with self.assertRaises(RuntimeError) as ctx:
            p11.assert_binary_identity(provenance_fn=drifted_provenance)
        message = str(ctx.exception)
        self.assertIn("f" * 64, message)
        self.assertIn(p11.RUSTKMER_BIN_SHA256, message)

    def test_pinned_hashes_pass_and_return_identity(self):
        """GREEN: the pinned hashes pass and the identity block returns."""
        identity = p11.assert_binary_identity(
            provenance_fn=fake_identity_provenance)
        self.assertEqual(identity["rustkmer"]["sha256"],
                         p11.RUSTKMER_BIN_SHA256)
        self.assertEqual(identity["jellyfish"]["sha256"],
                         p11.JELLYFISH_BIN_SHA256)
        p11.validate_provenance(identity["provenance"])


class TestParityDocBuilder(unittest.TestCase):
    """The parity-doc contract Plan 12-01's validator gates."""

    def test_builder_emits_three_legs_exact_anchors_warmup_merges(self):
        """legs_executed == the three legs; anchors.exact; warmup records."""
        doc = p11.parity_doc(
            k=21, anchors_exact_total=8_967_099_203,
            merges=[{"tool": "rustkmer", "warmup": True,
                     "argv": ["/bin/rustkmer", "merge"], "wall_s": 1.0},
                    {"tool": "jellyfish", "warmup": True,
                     "argv": ["jellyfish", "merge"], "wall_s": 2.0}],
            merged_stats={"rustkmer": {"distinct": 897266581,
                                       "total": 8_967_099_203},
                          "jellyfish": {"distinct": 897266581,
                                        "total": 8_967_099_203}},
            recount_stats={"distinct": 897266581, "total": 8_967_099_203,
                           "definition": "sum-of-counts"},
            input_revalidation={"anchors": "exact"},
            binary_identity={"rustkmer": {}, "jellyfish": {}},
            transients_deleted=["/scratch/recount.k21.rkdb"],
            provenance=fake_provenance())
        self.assertEqual(doc["legs_executed"],
                         ["leg1-aggregate-conservation",
                          "leg2-recount-vs-merged", "leg3-dump-vs-dump"])
        self.assertTrue(doc["anchors"]["exact"])
        self.assertEqual(doc["anchors"]["expected"], 8_967_099_203)
        self.assertEqual(doc["anchors"]["sum"], 8_967_099_203)
        for merge in doc["merges"]:
            self.assertTrue(merge["warmup"])
            self.assertIn("argv", merge)
        self.assertIn("/scratch/recount.k21.rkdb", doc["transients_deleted"])
        # Interface-first check: the emitted dict passes Plan 12-01's gate.
        p11._validate_parity_document(doc)

    def test_builder_rejects_inexact_anchors(self):
        """The builder never emits a doc whose anchors are not exact."""
        with self.assertRaises(ValueError):
            p11.parity_doc(
                k=21, anchors_exact_total=8_967_099_202,
                merges=[{"tool": "rustkmer", "warmup": True}],
                merged_stats={"rustkmer": {"distinct": 1, "total": 2},
                              "jellyfish": {"distinct": 1, "total": 2}},
                recount_stats={"distinct": 1, "total": 2},
                input_revalidation={}, binary_identity={},
                transients_deleted=[], provenance=fake_provenance())


if __name__ == "__main__":
    unittest.main()
