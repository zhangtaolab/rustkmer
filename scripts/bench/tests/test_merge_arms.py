"""Unit tests for the MBENCH-01 merge arm set: builders, ordering, threads.

Covers the three harness primitives the seven-arm comparison rides on:
`jellyfish_merge_cmd` (list-form argv, validate_path everywhere, no flag
copying between jellyfish subcommands), `build_merge_cmd(num_threads=...)`
(the merge-t1 like-for-like arm), and `assert_arm_ordering` (count arms
precede merge arms within each tool — the warmup-runs-first-spec guard).
One class per function under test, stdlib unittest only, following
test_merge_input.py conventions.
"""

import unittest

from scripts.bench.bench import (
    assert_arm_ordering,
    build_merge_cmd,
    jellyfish_merge_cmd,
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


if __name__ == "__main__":
    unittest.main()
