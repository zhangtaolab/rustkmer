"""Unit tests for the MBENCH-01 merge arm set: builders, ordering, threads.

Covers the three harness primitives the seven-arm comparison rides on:
`jellyfish_merge_cmd` (list-form argv, validate_path everywhere, no flag
copying between jellyfish subcommands), `build_merge_cmd(num_threads=...)`
(the merge-t1 like-for-like arm), and `assert_arm_ordering` (count arms
precede merge arms within each tool — the warmup-runs-first-spec guard).
One class per function under test, stdlib unittest only, following
test_merge_input.py conventions.

Also covers the MBENCH-02 three-way merge parity gate (PARITY-GATE.md):
`assert_merge_parity` GREEN/RED on every aggregate invariant,
`normalize_dump_lines` on both dump formats' fixture strings, and
`dump_vs_dump_equal` through its injectable dump seams — the live two-tool
comparator run stays out of the unit suite (binary-light).
"""

import unittest

from scripts.bench.bench import (
    assert_arm_ordering,
    assert_merge_parity,
    build_merge_cmd,
    dump_vs_dump_equal,
    jellyfish_merge_cmd,
    normalize_dump_lines,
)

SEVEN_ARM_ORDER = (
    ("count-A", "rustkmer"),
    ("count-B", "rustkmer"),
    ("merge", "rustkmer"),
    ("merge-t1", "rustkmer"),
    ("jellyfish-count-A", "jellyfish"),
    ("jellyfish-count-B", "jellyfish"),
    ("jellyfish-merge", "jellyfish"),
)


def spec(name, tool):
    """A minimal arm spec for ordering tests (only name and tool matter)."""
    return {"name": name, "tool": tool}


class TestJellyfishMergeCmd(unittest.TestCase):
    """jellyfish_merge_cmd: exact argv shape, loud rejections, no flags."""

    def test_argv_shape_is_exact_list_form(self):
        """The argv is exactly ["jellyfish", "merge", "-o", out, in1, in2]."""
        argv = jellyfish_merge_cmd("out.jf", ["in1.jf", "in2.jf"])
        self.assertEqual(
            argv, ["jellyfish", "merge", "-o", "out.jf", "in1.jf", "in2.jf"])

    def test_unsafe_path_rejected(self):
        """validate_path screens every path: unsafe characters raise."""
        with self.assertRaises(ValueError):
            jellyfish_merge_cmd("out; rm -rf.jf", ["in1.jf", "in2.jf"])
        with self.assertRaises(ValueError):
            jellyfish_merge_cmd("out.jf", ["$(touch pwn).jf", "in2.jf"])

    def test_no_count_flags_in_argv(self):
        """No -t, -s, or -m appears in the argv (flag-collision guard).

        In merge, -m is MIN mode — copying count's mer-length flag set here
        would silently change merge semantics (MBENCH-01 prohibition).
        """
        argv = jellyfish_merge_cmd("out.jf", ["in1.jf", "in2.jf"])
        for flag in ("-t", "-s", "-m", "-M", "-j"):
            self.assertNotIn(flag, argv)


class TestBuildMergeCmdThreads(unittest.TestCase):
    """build_merge_cmd num_threads: absent by default, exact when set."""

    def test_none_omits_num_threads(self):
        """num_threads=None produces argv without --num-threads (the 'merge'
        arm shape — the tool default of all cores applies)."""
        argv = build_merge_cmd("rk", "out.rkdb", ["a.rkdb", "b.rkdb"])
        self.assertNotIn("--num-threads", argv)
        self.assertEqual(
            argv, ["rk", "merge", "-i", "a.rkdb", "b.rkdb", "-o", "out.rkdb"])

    def test_one_appends_exact_flag_pair(self):
        """num_threads=1 appends exactly ['--num-threads', '1'] (the
        'merge-t1' arm shape — like-for-like single-thread, MBENCH-01)."""
        argv = build_merge_cmd("rk", "out.rkdb", ["a.rkdb", "b.rkdb"],
                               num_threads=1)
        self.assertEqual(
            argv, ["rk", "merge", "-i", "a.rkdb", "b.rkdb", "-o", "out.rkdb",
                   "--num-threads", "1"])


class TestAssertArmOrdering(unittest.TestCase):
    """assert_arm_ordering: GREEN on the shipped order, RED on violation.

    The invariant is generic over any arm list: within one tool's spec
    order, every count arm must precede every merge arm (the protocol's
    warmup executes the first spec per tool and same-tool arms run in spec
    order).
    """

    def test_green_on_shipped_seven_arm_order(self):
        """The shipped seven-arm spec order passes with no exception."""
        assert_arm_ordering(
            [spec(name, tool) for name, tool in SEVEN_ARM_ORDER])

    def test_red_when_merge_precedes_count_within_tool(self):
        """A merge arm before a count arm of the same tool raises."""
        bad = [spec("count-A", "rustkmer"),
               spec("merge", "rustkmer"),
               spec("count-B", "rustkmer")]
        with self.assertRaisesRegex(RuntimeError, "count-B.*follows.*merge"):
            assert_arm_ordering(bad)

    def test_red_on_jellyfish_merge_before_jellyfish_count_b(self):
        """jellyfish-merge preceding jellyfish-count-B raises."""
        bad = [spec("jellyfish-count-A", "jellyfish"),
               spec("jellyfish-merge", "jellyfish"),
               spec("jellyfish-count-B", "jellyfish")]
        with self.assertRaisesRegex(RuntimeError,
                                    "jellyfish-count-B.*jellyfish-merge"):
            assert_arm_ordering(bad)

    def test_red_when_merge_precedes_count_across_inserted_arm(self):
        """A count arm after merge arms even with another arm inserted
        between still raises (position-based, not adjacency-based)."""
        bad = [spec("count-A", "rustkmer"),
               spec("merge", "rustkmer"),
               spec("merge-t1", "rustkmer"),
               spec("count-C", "rustkmer")]
        with self.assertRaisesRegex(RuntimeError, "count-C"):
            assert_arm_ordering(bad)

    def test_generic_arm_names_obey_the_same_rule(self):
        """Any names containing 'count'/'merge' obey the rule — the
        invariant is not pinned to the current seven names."""
        assert_arm_ordering([spec("count-x", "t1"), spec("merge-y", "t1"),
                             spec("merge-z", "t1")])
        with self.assertRaises(RuntimeError):
            assert_arm_ordering([spec("merge-y", "t1"),
                                 spec("count-x", "t1")])

    def test_ordering_is_scoped_per_tool(self):
        """A merge-first order in one tool does not condemn another tool's
        arms — the check compares within each tool's spec order only."""
        cross = [spec("merge", "rustkmer"),
                 spec("count-A", "jellyfish"),
                 spec("merge", "jellyfish")]
        assert_arm_ordering(cross)  # must not raise


class TestAssertMergeParity(unittest.TestCase):
    """assert_merge_parity: GREEN on conserved arms, RED on every invariant.

    The gate's boundary semantics are pinned here (MBENCH-02/boundary):
    merged Distinct exactly at the max input Distinct passes; one count
    short raises. Every Total in these fixtures stands for the sum-of-counts
    definition carried on the arm dicts.
    """

    @staticmethod
    def arms(merge_total=900, jf_total=900, count_a_total=500,
             count_b_total=400, merge_distinct=300, jf_distinct=300,
             count_a_distinct=250, count_b_distinct=260):
        """A conserved fixture arm dict; keyword overrides bend one value."""
        return {
            "count-A": {"distinct_kmers": count_a_distinct,
                        "total_kmers": count_a_total},
            "count-B": {"distinct_kmers": count_b_distinct,
                        "total_kmers": count_b_total},
            "merge": {"distinct_kmers": merge_distinct,
                      "total_kmers": merge_total},
            "jellyfish-merge": {"distinct_kmers": jf_distinct,
                                "total_kmers": jf_total},
        }

    def test_green_on_conserved_fixture(self):
        """A fully conserved fixture (all four invariants hold) passes."""
        assert_merge_parity(self.arms())

    def test_green_at_exact_max_input_distinct_boundary(self):
        """Merged Distinct exactly equal to max input Distinct PASSES
        (the invariant is >=); the boundary is not a violation."""
        assert_merge_parity(
            self.arms(merge_distinct=260, jf_distinct=260,
                      count_b_distinct=260))

    def test_red_on_rustkmer_total_mismatch(self):
        """rustkmer merge Total != sum of input Totals raises (named as the
        sum-of-counts definition)."""
        with self.assertRaisesRegex(RuntimeError, "rustkmer merge Total"):
            assert_merge_parity(self.arms(merge_total=901))

    def test_red_on_jellyfish_total_mismatch(self):
        """jellyfish-merge Total != sum of input Totals raises."""
        with self.assertRaisesRegex(RuntimeError, "jellyfish-merge Total"):
            assert_merge_parity(self.arms(jf_total=899))

    def test_red_on_distinct_inequality(self):
        """Merged Distinct differing across tools (union key-spaces) raises."""
        with self.assertRaisesRegex(RuntimeError, "differs across tools"):
            assert_merge_parity(self.arms(jf_distinct=299))

    def test_red_on_distinct_below_max_input(self):
        """Merged Distinct one count below max input Distinct raises — the
        boundary case just short of the GREEN boundary test."""
        with self.assertRaisesRegex(RuntimeError, "max input Distinct"):
            assert_merge_parity(
                self.arms(merge_distinct=259, jf_distinct=259,
                          count_b_distinct=260))


class TestNormalizeDumpLines(unittest.TestCase):
    """normalize_dump_lines: both formats' fixtures, comments, fail-loud."""

    def test_parses_rustkmer_dump_fixture_skipping_comments(self):
        """'#' header lines and blank lines are skipped; data lines become
        'kmer<TAB>count' strings."""
        text = ("# rustkmer database dump\n"
                "# k: 5\n"
                "# total_kmers: 3\n"
                "\n"
                "ACGTAAA\t2\n"
                "ACGTAAC\t1\n")
        self.assertEqual(normalize_dump_lines(text),
                         ["ACGTAAA\t2", "ACGTAAC\t1"])

    def test_parses_jellyfish_dump_c_fixture(self):
        """`jellyfish dump -c` two-column lines parse identically; extra
        whitespace collapses to the single-tab normalized shape."""
        text = "ACGTAAG   3\nACGTAAT\t7\n"
        self.assertEqual(normalize_dump_lines(text),
                         ["ACGTAAG\t3", "ACGTAAT\t7"])

    def test_raises_on_malformed_line(self):
        """A line with the wrong field count or a non-integer count raises,
        naming the offending line — a tolerant parser would let the gate run
        against nothing (MBENCH-02/empty)."""
        for bad in ("ACGTAAA\t2\textra\n", "ACGTAAA\n", "ACGTAAA\tnotanint\n"):
            with self.assertRaisesRegex(RuntimeError, "ACGTAAA"):
                normalize_dump_lines(bad)

    def test_raises_on_empty_text(self):
        """Empty or comment-only input (zero data lines) raises — a zero-line
        dump can never pass."""
        for empty in ("", "   \n", "# rustkmer database dump\n# k: 5\n"):
            with self.assertRaises(RuntimeError):
                normalize_dump_lines(empty)


RK_DUMP_FIXTURE = ("# rustkmer database dump\n"
                   "# k: 5\n"
                   "ACGTAAC\t1\n"
                   "ACGTAAA\t2\n"
                   "ACGTAAG\t3\n")
JF_DUMP_FIXTURE = ("ACGTAAA\t2\n"
                   "ACGTAAC\t1\n"
                   "ACGTAAG\t3\n")


class TestDumpVsDumpEqual(unittest.TestCase):
    """dump_vs_dump_equal through its injectable dump seams (binary-light).

    The live two-tool comparator run on real merged artifacts is the Task 3
    slice-scale proof; these fixtures drive the real normalize/sort/compare
    logic on text only.
    """

    @staticmethod
    def run_with(rk_text, jf_text):
        """Call dump_vs_dump_equal with fixture-seamed dump helpers."""
        return dump_vs_dump_equal(
            "merged.rkdb", "merged.jf", "rustkmer", "/tmp",
            dump_rk=lambda path, rk, workdir: rk_text,
            dump_jf=lambda path, workdir: jf_text)

    def test_equal_fixture_pair_passes(self):
        """Byte-equal-after-normalize-and-sort fixtures return True."""
        self.assertTrue(self.run_with(RK_DUMP_FIXTURE, JF_DUMP_FIXTURE))

    def test_altered_count_fails_with_mismatch_report(self):
        """A single altered count line fails, naming the differing pair."""
        altered = JF_DUMP_FIXTURE.replace("ACGTAAG\t3", "ACGTAAG\t4")
        with self.assertRaisesRegex(RuntimeError,
                                    r"ACGTAAG\\t3.*ACGTAAG\\t4"):
            self.run_with(RK_DUMP_FIXTURE, altered)

    def test_length_mismatch_fails(self):
        """A k-mer present on only one side fails (length mismatch), even
        though every shared line agrees."""
        shorter = JF_DUMP_FIXTURE.replace("ACGTAAG\t3\n", "")
        with self.assertRaisesRegex(RuntimeError, "differ in length"):
            self.run_with(RK_DUMP_FIXTURE, shorter)

    def test_empty_side_fails_loudly(self):
        """An empty dump from either side raises — a zero-line dump can
        never pass (MBENCH-02/empty)."""
        with self.assertRaisesRegex(RuntimeError, "empty"):
            self.run_with("", JF_DUMP_FIXTURE)
        with self.assertRaisesRegex(RuntimeError, "empty"):
            self.run_with(RK_DUMP_FIXTURE, "")


if __name__ == "__main__":
    unittest.main()
