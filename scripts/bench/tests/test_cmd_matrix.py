"""Unit tests for the 04-02 fairness matrix + protocol primitives (BENCH-02).

Golden argv pairs pin that ONE BenchmarkConfig derives BOTH tools' command
lines with k mirrored (rustkmer -k == jellyfish -m), canonicalization
mirrored (-C in both), the thread literal identical, and gz input reaching
jellyfish only through the decompressor pipe with /dev/stdin — fairness is
encoded in code, not hand-copied between two builders.

validate_path is the T-04-03 mitigation (paths cross into the one sh -c
pipeline) and is unit-proven with hostile filenames. The protocol primitives
(round_schedule, cache_state_from, reduce_arm) pin the counterbalanced
multi-rep protocol's shape. Stdlib unittest only — no pytest, no conftest.
"""

import statistics
import unittest

from scripts.bench import bench

# Real `jellyfish stats` 2.3.1 output shape, captured verbatim on the dev host
# (key, colon, space-padding, integer — no percent column in 2.3.1).
JF_STATS_TEXT = ("Unique:    24000\n"
                 "Distinct:  24000\n"
                 "Total:     24000\n"
                 "Max_count: 1\n")

# Filenames a hostile dataset directory could carry; every one of these must
# be rejected by validate_path BEFORE any sh -c string is assembled (T-04-03).
HOSTILE_PATHS = [
    "read 1.fq.gz",            # whitespace
    "$(rm -rf /).fq",          # command substitution
    "`id`.fq",                 # backtick substitution
    "a;rm -rf .fq",            # statement separator
    "p|q.fq",                  # pipe
    "a&&b.fq",                 # AND-list
    "r>w.fq",                  # redirection
    "n\n.fq",                  # newline
    "q'q.fq",                  # single quote
    'd"d.fq',                  # double quote
    "e$f.fq",                  # variable expansion
    "(sub).fq",                # subshell
    "z*.fq",                   # glob
    "x?.fq",                   # glob
    "ind\\ex.fq",              # backslash escape
    "  .fq",                   # leading whitespace
]

HOSTILE_HASH_SIZES = ["10G; touch /tmp/pwned", "1M$(id)", "2G `id`",
                      "10G & echo x", "1G|wc"]


def _fn(name):
    """Fetch a bench symbol, failing the calling test with a clear assertion
    while the 04-02 implementation does not exist (TDD RED)."""
    fn = getattr(bench, name, None)
    assert fn is not None, f"bench.{name} is not implemented (04-02 Task 2)"
    return fn


def make_config(**overrides):
    """Build a BenchmarkConfig, failing the calling test with a clear
    assertion while the 04-02 config refactor has not landed (TDD RED)."""
    cfg_cls = getattr(bench, "BenchmarkConfig", None)
    assert cfg_cls is not None, "bench.BenchmarkConfig is not implemented (04-02 Task 2)"
    fields = dict(k=31, canonical=True, threads=16, hash_size="10G",
                  inputs=["/abs/read_1.fq.gz"], decompressor="gzcat")
    fields.update(overrides)
    return cfg_cls(**fields)


class TestGoldenArgvPairs(unittest.TestCase):
    """One BenchmarkConfig derives both tools' matched command lines."""

    def test_golden_argv_gz_input_pair(self):
        """k=31/threads=16/gz: rustkmer list form; jellyfish sh -c pipe."""
        cfg = make_config(k=31, threads=16, inputs=["/abs/read_1.fq.gz"])
        rk = _fn("rustkmer_count_cmd")(cfg, "/abs/out.rkdb")
        jf = _fn("jellyfish_count_cmd")(cfg, "/abs/out.jf")
        self.assertEqual(
            rk,
            ["target/release/rustkmer", "count", "-k", "31", "-C",
             "--threads", "16", "-o", "/abs/out.rkdb", "-i",
             "/abs/read_1.fq.gz"])
        self.assertEqual(
            jf,
            ["sh", "-c",
             "gzcat /abs/read_1.fq.gz | jellyfish count -m 31 -s 10G "
             "-t 16 -C -o /abs/out.jf /dev/stdin"])

    def test_golden_argv_plain_input_pair(self):
        """k=21/threads=8/plain: jellyfish takes direct path arguments."""
        cfg = make_config(k=21, threads=8, inputs=["in.fq"])
        rk = _fn("rustkmer_count_cmd")(cfg, "out.rkdb")
        jf = _fn("jellyfish_count_cmd")(cfg, "out.jf")
        self.assertEqual(
            rk,
            ["target/release/rustkmer", "count", "-k", "21", "-C",
             "--threads", "8", "-o", "out.rkdb", "-i", "in.fq"])
        self.assertEqual(
            jf,
            ["jellyfish", "count", "-m", "21", "-s", "10G", "-t", "8",
             "-C", "-o", "out.jf", "in.fq"])
        # Plain input never goes through the pipe: no shell, no /dev/stdin.
        self.assertNotIn("sh", jf)
        self.assertNotIn("/dev/stdin", jf)

    def test_k_mirrors_m_across_values(self):
        """rustkmer -k value == jellyfish -m value for several k."""
        for k in (21, 31, 51):
            cfg = make_config(k=k, inputs=["in.fq"])
            rk = _fn("rustkmer_count_cmd")(cfg, "o.rkdb")
            jf = _fn("jellyfish_count_cmd")(cfg, "o.jf")
            rk_k = rk[rk.index("-k") + 1]
            self.assertEqual(rk_k, str(k))
            if jf[0] == "sh":
                self.assertIn(f"-m {k} ", jf[2])
            else:
                self.assertEqual(jf[jf.index("-m") + 1], str(k))

    def test_canonical_flag_mirrored(self):
        """-C present in both argv iff cfg.canonical."""
        for canonical, present in ((True, True), (False, False)):
            cfg = make_config(canonical=canonical, inputs=["in.fq"])
            rk = _fn("rustkmer_count_cmd")(cfg, "o.rkdb")
            jf = _fn("jellyfish_count_cmd")(cfg, "o.jf")
            self.assertEqual(("-C" in rk), present)
            if jf[0] == "sh":
                self.assertEqual((" -C " in jf[2]) or
                                 jf[2].split()[-2] == "-C", present)
            else:
                self.assertEqual(("-C" in jf), present)

    def test_threads_literal_identical(self):
        """The thread count appears as the identical literal in both."""
        cfg = make_config(threads=8, inputs=["in.fq"])
        rk = _fn("rustkmer_count_cmd")(cfg, "o.rkdb")
        jf = _fn("jellyfish_count_cmd")(cfg, "o.jf")
        rk_t = rk[rk.index("--threads") + 1]
        if jf[0] == "sh":
            jf_t = jf[2].split()[jf[2].split().index("-t") + 1]
        else:
            jf_t = jf[jf.index("-t") + 1]
        self.assertEqual(rk_t, "8")
        self.assertEqual(rk_t, jf_t)

    def test_multiple_gz_inputs_feed_one_pipe(self):
        """All gz inputs decompress through ONE pipe into one jellyfish."""
        cfg = make_config(inputs=["/abs/a.fq.gz", "/abs/b.fq.gz"])
        jf = _fn("jellyfish_count_cmd")(cfg, "/abs/o.jf")
        self.assertEqual(jf[0], "sh")
        self.assertTrue(jf[2].startswith("gzcat /abs/a.fq.gz /abs/b.fq.gz |"))
        self.assertIn("/dev/stdin", jf[2])

    def test_builder_determinism(self):
        """Identical config -> byte-identical argv on repeated calls."""
        cfg_a = make_config(inputs=["/abs/a.fq.gz"])
        cfg_b = make_config(inputs=["/abs/a.fq.gz"])
        for _ in range(3):
            self.assertEqual(_fn("rustkmer_count_cmd")(cfg_a, "/abs/o.rkdb"),
                             _fn("rustkmer_count_cmd")(cfg_b, "/abs/o.rkdb"))
            self.assertEqual(_fn("jellyfish_count_cmd")(cfg_a, "/abs/o.jf"),
                             _fn("jellyfish_count_cmd")(cfg_b, "/abs/o.jf"))


class TestValidatePath(unittest.TestCase):
    """T-04-03: hostile paths are rejected before any shell string exists."""

    def test_accepts_absolute_gz_path(self):
        self.assertEqual(_fn("validate_path")("/abs/path/read_1.fq.gz"),
                         "/abs/path/read_1.fq.gz")

    def test_accepts_safe_relative_path(self):
        """Letters/digits/dot/slash/underscore/hyphen are the allowlist."""
        self.assertEqual(_fn("validate_path")("data/input_2024-01.fq"),
                         "data/input_2024-01.fq")

    def test_accepts_pathlib_path(self):
        import pathlib
        self.assertEqual(_fn("validate_path")(pathlib.Path("/abs/x.fq.gz")),
                         "/abs/x.fq.gz")

    def test_rejects_empty_path(self):
        with self.assertRaises(ValueError):
            _fn("validate_path")("")

    def test_rejects_hostile_filenames(self):
        """Every hostile filename raises ValueError naming the path."""
        for hostile in HOSTILE_PATHS:
            with self.assertRaises(ValueError) as ctx:
                _fn("validate_path")(hostile)
            self.assertIn(hostile, str(ctx.exception),
                          f"message must name the offending path {hostile!r}")

    def test_jellyfish_cmd_refuses_hostile_input(self):
        """The builder itself refuses hostile inputs (no sh -c assembled)."""
        for hostile in HOSTILE_PATHS[:6]:
            cfg = make_config(inputs=[f"/abs/{hostile}.gz"])
            with self.assertRaises(ValueError):
                _fn("jellyfish_count_cmd")(cfg, "/abs/o.jf")

    def test_jellyfish_cmd_refuses_hostile_hash_size(self):
        """--hash-size crosses into the sh -c string; only ^\\d+[KMG]?$."""
        for hostile in HOSTILE_HASH_SIZES:
            cfg = make_config(inputs=["/abs/a.fq.gz"], hash_size=hostile)
            with self.assertRaises(ValueError):
                _fn("jellyfish_count_cmd")(cfg, "/abs/o.jf")

    def test_jellyfish_cmd_refuses_hostile_output_path(self):
        cfg = make_config(inputs=["/abs/a.fq.gz"])
        with self.assertRaises(ValueError):
            _fn("jellyfish_count_cmd")(cfg, "/abs/ou t.jf")


class TestParseJellyfishStats(unittest.TestCase):
    """The parity gate's numbers come from this pure parser."""

    def test_extracts_distinct_and_total(self):
        self.assertEqual(bench.parse_jellyfish_stats(JF_STATS_TEXT),
                         {"distinct": 24000, "total": 24000})

    def test_missing_distinct_line_raises(self):
        with self.assertRaises(ValueError):
            bench.parse_jellyfish_stats("Unique:    24000\nTotal:     24000\n")

    def test_missing_total_line_raises(self):
        with self.assertRaises(ValueError):
            bench.parse_jellyfish_stats("Distinct:  24000\n")

    def test_empty_text_raises(self):
        with self.assertRaises(ValueError):
            bench.parse_jellyfish_stats("")


class TestProtocolPrimitives(unittest.TestCase):
    """Counterbalanced rounds, honest cache_state, median/CV reduction."""

    def test_round_schedule_counterbalances(self):
        """rustkmer first in even rounds, jellyfish first in odd rounds."""
        sched = _fn("round_schedule")(4)
        self.assertEqual(sched["0"], ["rustkmer", "jellyfish"])
        self.assertEqual(sched["1"], ["jellyfish", "rustkmer"])
        self.assertEqual(sched["2"], ["rustkmer", "jellyfish"])
        self.assertEqual(sched["3"], ["jellyfish", "rustkmer"])

    def test_round_schedule_two_rounds_minimum(self):
        self.assertEqual(_fn("round_schedule")(2),
                         {"0": ["rustkmer", "jellyfish"],
                          "1": ["jellyfish", "rustkmer"]})

    def test_cache_state_truth_table(self):
        """GITHUB_ACTIONS -> runner-fresh; non-darwin -> unavailable;
        darwin purge rc 0 -> purged; failure -> unavailable (T-04-04)."""
        f = _fn("cache_state_from")
        self.assertEqual(f(True, "darwin", None), "runner-fresh")
        self.assertEqual(f(True, "linux", None), "runner-fresh")
        self.assertEqual(f(False, "linux", None), "unavailable")
        self.assertEqual(f(False, "darwin", True), "purged")
        self.assertEqual(f(False, "darwin", False), "unavailable")

    def test_reduce_arm_medians_and_cv(self):
        """Median wall/RSS + CV% = stdev/mean*100, warning only above 10."""
        reps = [{"wall_s": 1.0, "peak_rss_bytes": 10},
                {"wall_s": 2.0, "peak_rss_bytes": 20},
                {"wall_s": 3.0, "peak_rss_bytes": 30}]
        out = _fn("reduce_arm")(reps)
        self.assertEqual(out["median_wall_s"], 2.0)
        self.assertEqual(out["median_peak_rss_bytes"], 20)
        expected_cv = statistics.stdev([1.0, 2.0, 3.0]) / 2.0 * 100
        self.assertAlmostEqual(out["cv_wall_pct"], expected_cv)
        self.assertFalse(out["cv_warning"])

    def test_reduce_arm_cv_warning_above_threshold(self):
        reps = [{"wall_s": 1.0, "peak_rss_bytes": 10},
                {"wall_s": 5.0, "peak_rss_bytes": 20}]
        out = _fn("reduce_arm")(reps)
        self.assertGreater(out["cv_wall_pct"], 10.0)
        self.assertTrue(out["cv_warning"])

    def test_reduce_arm_single_rep_records_null_cv(self):
        out = _fn("reduce_arm")([{"wall_s": 1.5, "peak_rss_bytes": 10}])
        self.assertEqual(out["median_wall_s"], 1.5)
        self.assertIsNone(out["cv_wall_pct"])
        self.assertFalse(out["cv_warning"])

    def test_default_decompressor(self):
        """gzcat on darwin; gunzip -c elsewhere (never macOS zcat)."""
        f = _fn("default_decompressor")
        self.assertEqual(f("darwin"), "gzcat")
        self.assertEqual(f("linux"), "gunzip -c")


if __name__ == "__main__":
    unittest.main()
