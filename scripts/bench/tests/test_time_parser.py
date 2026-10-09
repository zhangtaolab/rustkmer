"""Unit tests for the dual-platform /usr/bin/time output parser (BENCH-01).

Pins the units trap (RESEARCH Pitfall 2): macOS `-l` reports peak RSS in
bytes and must be taken as-is; Linux `-v` reports kbytes and must be scaled
x1024. A 1024x error here corrupts every downstream number. Stdlib unittest
only — no pytest, no conftest.
"""

import re
import unittest
from pathlib import Path

from scripts.bench.bench import parse_time_output

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# The literal integer in the captured macOS RSS line — extracted
# independently of the parser under test so equality proves no scaling.
MAC_RSS_LITERAL = re.compile(r"^\s*(\d+)\s+maximum resident set size\s*$")


class TestMacosParser(unittest.TestCase):
    """macOS `time -l` output (bytes, as-is)."""

    def test_fixture_wall_is_positive_float(self):
        """The real captured fixture yields a positive float wall-clock."""
        text = (FIXTURES / "time_l_macos.txt").read_text()
        result = parse_time_output(text, "darwin")
        self.assertIsInstance(result["wall_s"], float)
        self.assertGreater(result["wall_s"], 0.0)

    def test_fixture_peak_rss_is_raw_bytes(self):
        """Peak RSS equals the fixture's literal byte count (no scaling)."""
        text = (FIXTURES / "time_l_macos.txt").read_text()
        expected = None
        for line in text.splitlines():
            m = MAC_RSS_LITERAL.match(line)
            if m:
                expected = int(m.group(1))
                break
        self.assertIsNotNone(expected, "fixture must contain an RSS line")
        result = parse_time_output(text, "darwin")
        self.assertEqual(result["peak_rss_bytes"], expected)


class TestLinuxParser(unittest.TestCase):
    """Linux GNU `time -v` output (kbytes x 1024 -> bytes)."""

    def test_fixture_peak_rss_scaled_exactly(self):
        """62384 kbytes must parse to exactly 62384 * 1024 bytes."""
        text = (FIXTURES / "time_v_linux.txt").read_text()
        result = parse_time_output(text, "linux")
        self.assertEqual(result["peak_rss_bytes"], 62384 * 1024)

    def test_fixture_elapsed_mss_shape(self):
        """The fixture's '0:05.12' parses to 5.12 seconds."""
        text = (FIXTURES / "time_v_linux.txt").read_text()
        result = parse_time_output(text, "linux")
        self.assertAlmostEqual(result["wall_s"], 5.12)

    def test_elapsed_hmmss_shape(self):
        """An inline '1:23:45' elapsed line parses to 5025.0 seconds."""
        text = ("\tElapsed (wall clock) time (h:mm:ss or m:ss): 1:23:45\n"
                "\tMaximum resident set size (kbytes): 62384\n")
        result = parse_time_output(text, "linux")
        self.assertEqual(result["wall_s"], 5025.0)


class TestMalformedInput(unittest.TestCase):
    """Garbage or line-missing output must raise — never best-effort."""

    def test_empty_string_raises(self):
        """Empty time output raises ValueError."""
        with self.assertRaises(ValueError):
            parse_time_output("", "darwin")

    def test_missing_rss_line_raises(self):
        """Text with a wall line but no RSS line raises."""
        text = "        0.11 real         0.01 user         0.00 sys\n"
        with self.assertRaises(ValueError):
            parse_time_output(text, "darwin")

    def test_missing_wall_line_raises(self):
        """Text with an RSS line but no wall line raises."""
        text = "            9601024  maximum resident set size\n"
        with self.assertRaises(ValueError):
            parse_time_output(text, "darwin")

    def test_garbage_raises(self):
        """Unrelated prose raises instead of yielding invented numbers."""
        with self.assertRaises(ValueError):
            parse_time_output("complete garbage\nmore garbage\n", "darwin")

    def test_unsupported_platform_raises(self):
        """An unknown platform identifier raises."""
        with self.assertRaises(ValueError):
            parse_time_output("anything", "windows")


if __name__ == "__main__":
    unittest.main()
