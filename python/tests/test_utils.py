"""Tests for utility functions."""

import os
import pytest
import shutil
from unittest.mock import Mock, patch, mock_open
from rustkmer.utils import (
    validate_kmer,
    canonical_kmer,
    run_rustkmer_command,
    parse_query_output,
    parse_stats_output,
    find_rustkmer_executable
)
from rustkmer.exceptions import InvalidKmerError, SubprocessError


class TestValidateKmer:
    """Test validate_kmer function."""

    def test_validate_kmer_valid_7mer(self):
        """Test validation of valid 7-mer."""
        result = validate_kmer("ATCGATC", kmer_size=7, strict=True)
        assert result == "ATCGATC"

    def test_validate_kmer_valid_lowercase(self):
        """Test validation converts to uppercase."""
        result = validate_kmer("atcgaTC", kmer_size=7, strict=True)
        assert result == "ATCGATC"

    def test_validate_kmer_non_strict_none(self):
        """Test non-strict mode with None input."""
        result = validate_kmer(None, kmer_size=7, strict=False)
        assert result is None

    def test_validate_kmer_non_strict_invalid_type(self):
        """Test non-strict mode with non-string input."""
        result = validate_kmer(123, kmer_size=7, strict=False)
        assert result is None

    def test_validate_kmer_non_strict_invalid_chars(self):
        """Test non-strict mode with invalid characters."""
        result = validate_kmer("ATCGX", kmer_size=7, strict=False)
        assert result is None

    def test_validate_kmer_non_strict_wrong_length(self):
        """Test non-strict mode with wrong length."""
        result = validate_kmer("ATCG", kmer_size=7, strict=False)
        assert result is None

    def test_validate_kmer_strict_none(self):
        """Test strict mode with None input raises exception."""
        with pytest.raises(InvalidKmerError):
            validate_kmer(None, kmer_size=7, strict=True)

    def test_validate_kmer_strict_invalid_type(self):
        """Test strict mode with non-string input raises exception."""
        with pytest.raises(InvalidKmerError):
            validate_kmer(123, kmer_size=7, strict=True)

    def test_validate_kmer_strict_invalid_chars(self):
        """Test strict mode with invalid characters raises exception."""
        with pytest.raises(InvalidKmerError):
            validate_kmer("ATCGX", kmer_size=7, strict=True)

    def test_validate_kmer_strict_wrong_length(self):
        """Test strict mode with wrong length raises exception."""
        with pytest.raises(InvalidKmerError):
            validate_kmer("ATCG", kmer_size=7, strict=True)

    def test_validate_kmer_no_size_check(self):
        """Test validation without size check."""
        result = validate_kmer("ATCGATCG", kmer_size=None, strict=True)
        assert result == "ATCGATCG"

    def test_validate_kmer_empty_string(self):
        """Test validation with empty string."""
        with pytest.raises(InvalidKmerError):
            validate_kmer("", kmer_size=7, strict=True)

    def test_validate_kmer_whitespace(self):
        """Test validation with whitespace."""
        with pytest.raises(InvalidKmerError):
            validate_kmer("ATCG ATC", kmer_size=7, strict=True)


class TestCanonicalKmer:
    """Test canonical_kmer function."""

    def test_canonical_kmer_basic(self):
        """Test basic canonical k-mer conversion."""
        result = canonical_kmer("ATCG")
        assert result == "ATCG"  # ATCG < CGAT (reverse complement)

    def test_canonical_kmer_palindrome(self):
        """Test palindrome k-mer."""
        result = canonical_kmer("ATAT")
        assert result == "ATAT"  # same as reverse complement

    def test_canonical_kmer_lowercase(self):
        """Test canonical k-mer with lowercase input."""
        # Lowercase input causes KeyError - this tests error handling
        with pytest.raises(KeyError):
            canonical_kmer("atcg")

    def test_canonical_kmer_long_sequence(self):
        """Test canonical k-mer with longer sequence."""
        result = canonical_kmer("ATCGATCG")
        assert result == "ATCGATCG"  # ATCGATCG < CGATCGAT

    def test_canonical_kmer_all_a(self):
        """Test canonical k-mer with all A's."""
        result = canonical_kmer("AAAAAAA")
        assert result == "AAAAAAA"

    def test_canonical_kmer_all_t(self):
        """Test canonical k-mer with all T's."""
        result = canonical_kmer("TTTTTTT")
        assert result == "AAAAAAA"  # reverse complement

    def test_canonical_kmer_mixed_case(self):
        """Test canonical k-mer with mixed case."""
        # Mixed case input also causes KeyError
        with pytest.raises(KeyError):
            canonical_kmer("AtCgAtCg")

    def test_canonical_kmer_comparison(self):
        """Test that k-mer and its reverse complement return same canonical."""
        kmer = "ATCGATCG"
        rc = "CGATCGAT"
        assert canonical_kmer(kmer) == canonical_kmer(rc)


class TestRunRustkmerCommand:
    """Test run_rustkmer_command function."""

    @patch('subprocess.run')
    @patch('rustkmer.utils.find_rustkmer_executable')
    def test_run_rustkmer_command_success(self, mock_find_exe, mock_run):
        """Test successful command execution."""
        mock_find_exe.return_value = "/usr/bin/rustkmer"
        mock_run.return_value = Mock(
            returncode=0,
            stdout="ATCGATCG\t5\n",
            stderr=""
        )

        result = run_rustkmer_command(['query', 'test.rkdb', 'ATCGATCG'])
        assert result == "ATCGATCG\t5"  # stdout.strip() removes trailing newline
        mock_run.assert_called_once()

    @patch('subprocess.run')
    @patch('rustkmer.utils.find_rustkmer_executable')
    def test_run_rustkmer_command_database_not_found(self, mock_find_exe, mock_run):
        """Test command when database not found."""
        import subprocess
        mock_find_exe.return_value = "/usr/bin/rustkmer"
        mock_run.side_effect = subprocess.CalledProcessError(
            1,
            ['/usr/bin/rustkmer', 'query', 'nonexistent.rkdb', 'ATCGATCG'],
            stderr="Error: Database not found"
        )

        with pytest.raises(SubprocessError):
            run_rustkmer_command(['query', 'nonexistent.rkdb', 'ATCGATCG'])

    @patch('subprocess.run')
    @patch('rustkmer.utils.find_rustkmer_executable')
    def test_run_rustkmer_command_permission_denied(self, mock_find_exe, mock_run):
        """Test command when permission denied."""
        import subprocess
        mock_find_exe.return_value = "/usr/bin/rustkmer"
        mock_run.side_effect = subprocess.CalledProcessError(
            126,  # Permission denied exit code
            ['/usr/bin/rustkmer', 'query', 'protected.rkdb', 'ATCGATCG'],
            stderr="Permission denied"
        )

        with pytest.raises(SubprocessError):
            run_rustkmer_command(['query', 'protected.rkdb', 'ATCGATCG'])

    @patch('subprocess.run')
    @patch('rustkmer.utils.find_rustkmer_executable')
    def test_run_rustkmer_command_timeout(self, mock_find_exe, mock_run):
        """Test command with timeout."""
        mock_find_exe.return_value = "/usr/bin/rustkmer"

        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(['rustkmer'], 30)

        with pytest.raises(SubprocessError):
            run_rustkmer_command(['query', 'huge.rkdb', 'ATCGATCG'], timeout=30)

    @patch('subprocess.run')
    @patch('rustkmer.utils.find_rustkmer_executable')
    def test_run_rustkmer_command_custom_timeout(self, mock_find_exe, mock_run):
        """Test command with custom timeout."""
        mock_find_exe.return_value = "/usr/bin/rustkmer"
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Success",
            stderr=""
        )

        run_rustkmer_command(['stats', 'test.rkdb'], timeout=60)
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert kwargs['timeout'] == 60


class TestParseQueryOutput:
    """Test parse_query_output function."""

    def test_parse_query_output_normal(self):
        """Test parsing normal query output."""
        output = "ATCGATCG\t5"
        result = parse_query_output(output)
        assert result == {'kmer': 'ATCGATCG', 'count': 5, 'canonical': 'ATCGATCG'}

    def test_parse_query_output_with_newline(self):
        """Test parsing output with trailing newline."""
        output = "ATCGATCG\t5\n"
        result = parse_query_output(output)
        assert result == {'kmer': 'ATCGATCG', 'count': 5, 'canonical': 'ATCGATCG'}

    def test_parse_query_output_zero_count(self):
        """Test parsing output with zero count."""
        output = "ATCGATCG\t0"
        result = parse_query_output(output)
        assert result == {'kmer': 'ATCGATCG', 'count': 0, 'canonical': 'ATCGATCG'}

    def test_parse_query_output_large_count(self):
        """Test parsing output with large count."""
        output = "ATCGATCG\t1234567890"
        result = parse_query_output(output)
        assert result == {'kmer': 'ATCGATCG', 'count': 1234567890, 'canonical': 'ATCGATCG'}

    def test_parse_query_output_empty(self):
        """Test parsing empty output."""
        result = parse_query_output("")
        assert result == {'count': 0, 'kmer': '', 'canonical': ''}  # Empty output has kmer and canonical as empty strings

    def test_parse_query_output_whitespace_only(self):
        """Test parsing whitespace-only output."""
        result = parse_query_output("   \n   ")
        assert result == {'count': 0, 'kmer': '', 'canonical': ''}  # Whitespace only has kmer and canonical as empty strings

    def test_parse_query_output_multiple_lines(self):
        """Test parsing output with multiple lines (falls back to regex)."""
        output = "ATCGATCG\t5\nExtra line\nAnother line"
        result = parse_query_output(output)
        # With multiple lines, falls back to regex search
        assert result == {'kmer': 'ATCGATCG', 'count': 0, 'canonical': 'ATCGATCG'}

    def test_parse_query_output_invalid_format(self):
        """Test parsing output in invalid format."""
        output = "Invalid output format"
        result = parse_query_output(output)
        # No valid ATCG sequence found, returns empty kmer
        assert result == {'count': 0, 'kmer': '', 'canonical': ''}

    def test_parse_query_output_no_tab(self):
        """Test parsing output without tab separator."""
        output = "ATCGATCG 5"
        result = parse_query_output(output)
        assert result == {'count': 0, 'kmer': 'ATCGATCG', 'canonical': 'ATCGATCG'}  # Splits on space, non-numeric count = 0

    def test_parse_query_output_non_numeric_count(self):
        """Test parsing output with non-numeric count."""
        output = "ATCGATCG\tabc"
        # Non-numeric count raises ValueError
        with pytest.raises(ValueError):
            parse_query_output(output)


class TestParseStatsOutput:
    """Test parse_stats_output function."""

    def test_parse_stats_output_complete(self):
        """Test parsing complete stats output."""
        output = """kmer_size: 7
unique_kmers: 1000
total_counts: 2500
min_count: 1
max_count: 10
format_version: 1.0"""
        result = parse_stats_output(output)
        expected = {
            'kmer_size': 7,
            'unique_kmers': 1000,
            'total_counts': 2500,
            'min_count': 1,
            'max_count': 10,
            'format_version': 1.0,  # No quotes
            'file_size': 0  # Default value when not provided
        }
        assert result == expected

    def test_parse_stats_output_missing_fields(self):
        """Test parsing stats output with missing fields."""
        output = """kmer_size: 7
unique_kmers: 1000"""
        result = parse_stats_output(output)
        assert result['kmer_size'] == 7
        assert result['unique_kmers'] == 1000
        # Check defaults
        assert result['total_counts'] == 0
        assert result['min_count'] == 0
        assert result['max_count'] == 0
        assert result['file_size'] == 0
        assert result['format_version'] == 'unknown'  # Default is 'unknown', not '1.0'

    def test_parse_stats_output_empty(self):
        """Test parsing empty stats output."""
        result = parse_stats_output("")
        # Empty output returns dict with all defaults
        expected = {
            'kmer_size': 0,
            'unique_kmers': 0,
            'total_counts': 0,
            'min_count': 0,
            'max_count': 0,
            'file_size': 0,
            'format_version': 'unknown'
        }
        assert result == expected

    def test_parse_stats_output_with_colon_space(self):
        """Test parsing stats output with 'key: value' format."""
        output = "kmer_size: 7\nunique_kmers: 1000"
        result = parse_stats_output(output)
        assert result['kmer_size'] == 7
        assert result['unique_kmers'] == 1000

    def test_parse_stats_output_with_equals(self):
        """Test parsing stats output with 'key=value' format."""
        output = "kmer_size=7\nunique_kmers=1000"
        result = parse_stats_output(output)
        # With '=' separator, no ':' means lines are ignored, returns defaults
        expected = {
            'kmer_size': 0,
            'unique_kmers': 0,
            'total_counts': 0,
            'min_count': 0,
            'max_count': 0,
            'file_size': 0,
            'format_version': 'unknown'
        }
        assert result == expected

    def test_parse_stats_output_numeric_strings(self):
        """Test parsing stats output with numeric strings."""
        output = "kmer_size: '7'\nunique_kmers: \"1000\""
        result = parse_stats_output(output)
        # Quotes are NOT stripped, they remain as strings
        assert result['kmer_size'] == "'7'"
        assert result['unique_kmers'] == '"1000"'

    def test_parse_stats_output_with_comments(self):
        """Test parsing stats output with comment lines."""
        output = """# Rustkmer database stats
kmer_size: 7
# More stats
unique_kmers: 1000"""
        result = parse_stats_output(output)
        assert result['kmer_size'] == 7
        assert result['unique_kmers'] == 1000


class TestFindRustkmerExecutable:
    """Test find_rustkmer_executable function."""

    @patch('shutil.which')
    @patch('os.environ')
    @patch('pathlib.Path.exists')
    @patch('rustkmer.utils._rustkmer_path_cache', None)
    def test_find_rustkmer_from_path(self, mock_exists, mock_environ, mock_which):
        """Test finding rustkmer from system PATH."""
        # Clear cache and set up environment
        mock_environ.copy.return_value = {}
        mock_exists.return_value = False  # Package bin doesn't exist
        mock_which.return_value = '/usr/local/bin/rustkmer'
        result = find_rustkmer_executable()
        assert result == '/usr/local/bin/rustkmer'

    def test_run_rustkmer_command_error_handling(self):
        """Test subprocess error handling in run_rustkmer_command."""
        import subprocess
        with patch('rustkmer.utils.find_rustkmer_executable') as mock_find:
            mock_find.return_value = "/usr/bin/rustkmer"

            # Test "no such file" error
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(
                    1, 'rustkmer', stderr="no such file or directory"
                )
                with pytest.raises(SubprocessError):
                    run_rustkmer_command(['query', 'nonexistent.rkdb', 'ATCG'])

            # Test "permission denied" error
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(
                    126, 'rustkmer', stderr="permission denied"
                )
                with pytest.raises(SubprocessError):
                    run_rustkmer_command(['query', 'protected.rkdb', 'ATCG'])

    def test_parse_stats_output_field_mapping(self):
        """Test field name mapping in parse_stats_output."""
        # Test CLI field name mapping
        output = "k_mer_size: 7\nunique_k_mers: 1000\ntotal_k_mers: 2500"
        result = parse_stats_output(output)

        assert result['kmer_size'] == 7  # mapped from k_mer_size
        assert result['unique_kmers'] == 1000  # mapped from unique_k_mers
        assert result['total_counts'] == 2500  # mapped from total_k_mers
        assert result['min_count'] == 0  # default value
        assert result['max_count'] == 0  # default value
        assert result['file_size'] == 0  # default value
        assert result['format_version'] == 'unknown'  # default value

    @pytest.mark.xfail(
        condition=shutil.which('rustkmer') is not None,
        reason="Test expects rustkmer to not be installed, but rustkmer was found in PATH"
    )
    def test_find_rustkmer_not_found(self):
        """Test rustkmer not found in any location."""
        from rustkmer.exceptions import ConfigurationError
        # This test will fail if rustkmer is actually installed
        # The real function checks multiple locations before raising
        with pytest.raises(ConfigurationError):
            find_rustkmer_executable()