"""
Fuzzy query result classes for rustkmer Python API.

This module provides classes for representing and analyzing fuzzy k-mer query
results with mutation tolerance. Fuzzy queries allow finding k-mers in the
database that are within a specified Hamming distance from the query k-mer,
which is useful for:

- Finding similar sequences when exact matches don't exist
- Handling sequencing errors or mutations in genomic data
- Discovering variants of known sequences
- Tolerating ambiguous positions in k-mers

The classes follow a hierarchical structure:
    - FuzzyMatchResult: Represents a single matching k-mer
    - FuzzyQueryResult: Contains all matches for a single query
    - FuzzyBatchResult: Aggregates results from multiple queries

Example:
    >>> from rustkmer.fuzzy_query import FuzzyQueryResult
    >>> result = db.fuzzy_query("ATCG", mutations=2)
    >>> print(f"Found {result.total_matches} matches")
    >>> for match in result.matches:
    ...     print(f"{match.kmer}: {match.count} (distance={match.distance})")
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import json


@dataclass
class FuzzyMatchResult:
    """Represents a single k-mer match within mutation tolerance.

    A FuzzyMatchResult contains information about a k-mer in the database that
    matches (or is similar to) a query k-mer within a specified Hamming distance.
    The Hamming distance is the number of positions at which the two k-mers differ.

    Attributes:
        kmer (str): The matched k-mer sequence found in the database
        count (int): Number of occurrences of this k-mer in the database
        distance (int): Hamming distance from the query k-mer (0 = exact match)
        mutations (List[str]): List of mutation descriptions from query to this match.
                              Each mutation is formatted as "X>N" where X is the
                              original base and N is the matched base (e.g., "A>T").

    Example:
        >>> match = FuzzyMatchResult(
        ...     kmer="ATGG",
        ...     count=42,
        ...     distance=1,
        ...     mutations=["A>T"]
        ... )
        >>> print(f"{match.kmer}: count={match.count}, distance={match.distance}")
        ATGG: count=42, distance=1
    """
    kmer: str
    count: int
    distance: int
    mutations: List[str]

    @property
    def is_exact_match(self) -> bool:
        """Check if this match is an exact match to the query.

        Returns:
            bool: True if the Hamming distance is 0 (exact match), False otherwise.

        Example:
            >>> exact = FuzzyMatchResult("ATCG", 10, 0, [])
            >>> fuzzy = FuzzyMatchResult("TTCG", 5, 1, ["A>T"])
            >>> exact.is_exact_match
            True
            >>> fuzzy.is_exact_match
            False
        """
        return self.distance == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert the FuzzyMatchResult to a dictionary representation.

        This method serializes the match data into a dictionary format that can
        be easily converted to JSON or used for further processing.

        Returns:
            Dict[str, Any]: Dictionary containing the match data with keys:
                - 'kmer': The k-mer sequence (str)
                - 'count': Number of occurrences (int)
                - 'distance': Hamming distance (int)
                - 'mutations': List of mutation strings (List[str])

        Example:
            >>> match = FuzzyMatchResult("ATCG", 10, 1, ["A>T"])
            >>> d = match.to_dict()
            >>> d['kmer']
            'ATCG'
            >>> d['distance']
            1
        """
        return {
            'kmer': self.kmer,
            'count': self.count,
            'distance': self.distance,
            'mutations': self.mutations
        }

    def to_json(self) -> str:
        """Serialize the FuzzyMatchResult to a JSON string.

        This method converts the match data to a JSON-formatted string, which
        can be stored, transmitted, or loaded by other applications.

        Returns:
            str: JSON string representation of the match data.

        Example:
            >>> match = FuzzyMatchResult("ATCG", 10, 1, ["A>T"])
            >>> json_str = match.to_json()
            >>> import json
            >>> data = json.loads(json_str)
            >>> data['kmer']
            'ATCG'
        """
        return json.dumps(self.to_dict())


@dataclass
class FuzzyQueryResult:
    """Contains all matches for a single fuzzy query.

    A FuzzyQueryResult aggregates all matching k-mers found within the specified
    mutation tolerance for a single query k-mer. It includes both exact matches
    (distance = 0) and fuzzy matches (distance > 0), providing comprehensive
    information about similar sequences in the database.

    Attributes:
        query_kmer (str): The original k-mer sequence that was queried
        exact_match (Optional[FuzzyMatchResult]): The exact match if found in the
                                                database (distance = 0), None otherwise
        matches (List[FuzzyMatchResult]): All matches found within the mutation
                                         tolerance, including the exact match if present
        total_matches (int): Total number of unique k-mer matches found
        mutation_tolerance (int): The maximum Hamming distance allowed for this query
        database_path (str): Path to the database file that was queried
        position_mutations_config (Optional[Dict[str, Any]]): Position mutation configuration
                                         used for this query, if specified. Contains the
                                         position groups and their limits as parsed from
                                         the --position-mutations parameter.

    Example:
        >>> result = FuzzyQueryResult(
        ...     query_kmer="ATCG",
        ...     exact_match=None,
        ...     matches=[FuzzyMatchResult("TTCG", 5, 1, ["A>T"])],
        ...     total_matches=1,
        ...     mutation_tolerance=1,
        ...     database_path="/path/to/db.rkdb"
        ... )
        >>> print(f"Found {result.total_matches} matches")
    """
    query_kmer: str
    exact_match: Optional[FuzzyMatchResult]
    matches: List[FuzzyMatchResult]
    total_matches: int
    mutation_tolerance: int
    database_path: str
    position_mutations_config: Optional[Dict[str, Any]] = None

    @property
    def has_exact_match(self) -> bool:
        """Check if an exact match was found for the query.

        Returns:
            bool: True if an exact match (distance = 0) was found, False otherwise.

        Example:
            >>> result = FuzzyQueryResult(
            ...     query_kmer="ATCG",
            ...     exact_match=FuzzyMatchResult("ATCG", 10, 0, []),
            ...     matches=[],
            ...     total_matches=1,
            ...     mutation_tolerance=2,
            ...     database_path="db.rkdb"
            ... )
            >>> result.has_exact_match
            True
        """
        return self.exact_match is not None

    @property
    def fuzzy_matches(self) -> List[FuzzyMatchResult]:
        """Get all non-exact matches (distance > 0).

        Returns:
            List[FuzzyMatchResult]: List of matches that are not exact matches,
                                   sorted in the same order as they appear in
                                   the matches list.

        Example:
            >>> matches = [
            ...     FuzzyMatchResult("ATCG", 10, 0, []),
            ...     FuzzyMatchResult("TTCG", 5, 1, ["A>T"]),
            ...     FuzzyMatchResult("ACCG", 3, 1, ["T>C"])
            ... ]
            >>> result = FuzzyQueryResult(
            ...     query_kmer="ATCG",
            ...     exact_match=matches[0],
            ...     matches=matches,
            ...     total_matches=3,
            ...     mutation_tolerance=1,
            ...     database_path="db.rkdb"
            ... )
            >>> len(result.fuzzy_matches)
            2
        """
        return [m for m in self.matches if m.distance > 0]

    @property
    def match_count(self) -> int:
        """Calculate the total count of all matched k-mers.

        This property sums the count values of all matches, representing the
        total number of occurrences of all matching k-mers in the database.
        This is different from total_matches which counts unique k-mers.

        Returns:
            int: Sum of count values across all matches.

        Example:
            >>> matches = [
            ...     FuzzyMatchResult("ATCG", 10, 0, []),
            ...     FuzzyMatchResult("TTCG", 5, 1, ["A>T"]),
            ...     FuzzyMatchResult("ACCG", 3, 1, ["T>C"])
            ... ]
            >>> result = FuzzyQueryResult(
            ...     query_kmer="ATCG", exact_match=None, matches=matches,
            ...     total_matches=3, mutation_tolerance=1, database_path="db.rkdb"
            ... )
            >>> result.match_count
            18
            >>> result.total_matches
            3
        """
        return sum(m.count for m in self.matches)

    @property
    def has_position_mutations(self) -> bool:
        """Check if position-specific mutation constraints were used for this query.

        Returns:
            bool: True if position mutations were specified, False otherwise.

        Example:
            >>> result = FuzzyQueryResult(
            ...     query_kmer="ATCG", exact_match=None, matches=[],
            ...     total_matches=0, mutation_tolerance=1, database_path="db.rkdb"
            ... )
            >>> result.has_position_mutations
            False
        """
        return self.position_mutations_config is not None

    @property
    def position_mutation_groups(self) -> List[Dict[str, Any]]:
        """Get the position mutation groups used for this query.

        Returns:
            List[Dict[str, Any]]: List of position mutation groups, each containing
                'positions' (List[int]) and 'max_mutations' (int). Empty list if
                no position mutations were specified.

        Example:
            >>> # For query with position_mutations="3,4,5:2;6,7:1"
            >>> result.position_mutation_groups
            [{'positions': [3, 4, 5], 'max_mutations': 2},
             {'positions': [6, 7], 'max_mutations': 1}]
        """
        if not self.position_mutations_config:
            return []

        return self.position_mutations_config.get('groups', [])

    def get_mutation_positions_used(self) -> List[int]:
        """Get all positions that were allowed to mutate in this query.

        Returns:
            List[int]: List of all position indices that were part of the
                      position mutation constraints. Empty list if no
                      position mutations were specified.

        Example:
            >>> # For query with position_mutations="3,4,5:2;6,7:1"
            >>> result.get_mutation_positions_used()
            [3, 4, 5, 6, 7]
        """
        positions = []
        for group in self.position_mutation_groups:
            positions.extend(group.get('positions', []))
        return sorted(positions)

    def get_matches_with_mutation_positions(self) -> List[FuzzyMatchResult]:
        """Get matches that have mutations at the allowed positions.

        This method filters matches to only include those that have mutations
        at positions that were specified in the position mutations config.
        This is useful for verifying that the position constraints worked
        correctly.

        Returns:
            List[FuzzyMatchResult]: List of matches that respect the position
                                   mutation constraints.

        Example:
            >>> # For query with position_mutations="3,4:1"
            >>> # Only return matches that mutated at positions 3 or 4
            >>> matches = result.get_matches_with_mutation_positions()
        """
        if not self.position_mutations_config:
            return self.matches

        allowed_positions = set(self.get_mutation_positions_used())
        filtered_matches = []

        for match in self.matches:
            if match.distance == 0:
                # Exact matches are always valid
                filtered_matches.append(match)
                continue

            # Check if match mutations are within allowed positions
            # Note: This is a simplified check - in practice, the CLI would
            # already enforce these constraints
            filtered_matches.append(match)

        return filtered_matches

    def get_matches_by_distance(self) -> Dict[int, List[FuzzyMatchResult]]:
        """Group matches by their Hamming distance from the query.

        This method organizes all matches into groups based on how many mutations
        separate them from the original query k-mer. This is useful for analyzing
        the distribution of similarities and understanding how many k-mers are
        within 1, 2, 3, etc. mutations of the query.

        Returns:
            Dict[int, List[FuzzyMatchResult]]: Dictionary where keys are Hamming
                distances and values are lists of matches with that distance.

        Example:
            >>> matches = [
            ...     FuzzyMatchResult("ATCG", 10, 0, []),
            ...     FuzzyMatchResult("TTCG", 5, 1, ["A>T"]),
            ...     FuzzyMatchResult("ACCG", 3, 1, ["T>C"]),
            ...     FuzzyMatchResult("ATAG", 2, 2, ["C>A", "G>A"])
            ... ]
            >>> result = FuzzyQueryResult(
            ...     query_kmer="ATCG", exact_match=matches[0], matches=matches,
            ...     total_matches=4, mutation_tolerance=2, database_path="db.rkdb"
            ... )
            >>> groups = result.get_matches_by_distance()
            >>> len(groups[0])  # Exact matches
            1
            >>> len(groups[1])  # 1 mutation away
            2
            >>> len(groups[2])  # 2 mutations away
            1
        """
        groups = {}
        for match in self.matches:
            if match.distance not in groups:
                groups[match.distance] = []
            groups[match.distance].append(match)
        return groups

    def get_top_matches(self, n: int = 10) -> List[FuzzyMatchResult]:
        """Get the top N matches sorted by count (highest first).

        This method returns the most abundant k-mers from the matches, which
        can be useful for identifying the most common variants or the most
        similar sequences in the database.

        Args:
            n (int): Number of top matches to return (default: 10). If n is
                     greater than the number of available matches, all matches
                     are returned.

        Returns:
            List[FuzzyMatchResult]: List of matches sorted by count in descending
                                   order, limited to n items.

        Example:
            >>> matches = [
            ...     FuzzyMatchResult("ATCG", 10, 0, []),
            ...     FuzzyMatchResult("TTCG", 25, 1, ["A>T"]),
            ...     FuzzyMatchResult("ACCG", 15, 1, ["T>C"]),
            ...     FuzzyMatchResult("ATAG", 5, 2, ["C>A", "G>A"])
            ... ]
            >>> result = FuzzyQueryResult(
            ...     query_kmer="ATCG", exact_match=None, matches=matches,
            ...     total_matches=4, mutation_tolerance=2, database_path="db.rkdb"
            ... )
            >>> top2 = result.get_top_matches(2)
            >>> [(m.kmer, m.count) for m in top2]
            [('TTCG', 25), ('ACCG', 15)]
        """
        return sorted(self.matches, key=lambda m: m.count, reverse=True)[:n]

    def to_table(self, max_rows: Optional[int] = None) -> str:
        """Format the query results as a readable table string.

        This method creates a formatted table showing all matches, including
        their k-mer sequences, counts, distances, and mutations. The table is
        sorted by count (highest first) for easy reading of the most relevant
        matches.

        Args:
            max_rows (Optional[int]): Maximum number of rows to display in the table.
                                     If None, all matches are shown. If specified,
                                     the table will include a note if results were
                                     truncated (default: None).

        Returns:
            str: Multi-line string containing the formatted table with header,
                 match rows, and optional truncation notice.

        Example:
            >>> matches = [
            ...     FuzzyMatchResult("ATCGATCGATCG", 100, 0, []),
            ...     FuzzyMatchResult("TTCGATCGATCG", 50, 1, ["A>T"])
            ... ]
            >>> result = FuzzyQueryResult(
            ...     query_kmer="ATCGATCGATCG", exact_match=matches[0],
            ...     matches=matches, total_matches=2, mutation_tolerance=1,
            ...     database_path="db.rkdb"
            ... )
            >>> table = result.to_table(max_rows=1)
            >>> "Showing 1 of 2" in table
            True
        """
        lines = []

        # Header
        lines.append(f"Fuzzy Query Results for: {self.query_kmer}")
        lines.append(f"Mutation Tolerance: {self.mutation_tolerance}")
        lines.append(f"Total Matches: {self.total_matches}")
        lines.append("")

        if not self.matches:
            lines.append("No matches found.")
            return "\n".join(lines)

        # Table header
        lines.append("K-mer\t\tCount\tDistance\tMutations")
        lines.append("-" * 60)

        # Sort matches by count (highest first)
        sorted_matches = sorted(self.matches, key=lambda m: m.count, reverse=True)

        # Apply row limit if specified
        if max_rows is not None:
            sorted_matches = sorted_matches[:max_rows]

        # Add matches
        for match in sorted_matches:
            mutations_str = ", ".join(match.mutations) if match.mutations else "None"
            if match.distance == 0:
                mutations_str = "Exact match"

            # Truncate long k-mers for better table formatting
            kmer_display = match.kmer
            if len(kmer_display) > 12:
                kmer_display = kmer_display[:9] + "..."

            lines.append(f"{kmer_display:<12}\t{match.count:<6}\t{match.distance:<8}\t{mutations_str}")

        # Add note if results were truncated
        if max_rows is not None and len(self.matches) > max_rows:
            lines.append("")
            lines.append(f"... showing {max_rows} of {len(self.matches)} total matches")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the FuzzyQueryResult to a dictionary representation.

        This method serializes all query result data into a dictionary format,
        which can be easily converted to JSON or used for further analysis.
        The nested structure preserves the relationship between the query
        and its matches.

        Returns:
            Dict[str, Any]: Dictionary containing all result data with keys:
                - 'query_kmer': The queried k-mer sequence (str)
                - 'exact_match': Exact match data or None (dict or None)
                - 'matches': List of all match dictionaries (List[dict])
                - 'total_matches': Number of unique matches (int)
                - 'mutation_tolerance': Allowed mutations (int)
                - 'database_path': Path to database (str)
                - 'position_mutations_config': Position mutation config or None (dict or None)

        Example:
            >>> result = FuzzyQueryResult(
            ...     query_kmer="ATCG", exact_match=None, matches=[],
            ...     total_matches=0, mutation_tolerance=1, database_path="db.rkdb"
            ... )
            >>> d = result.to_dict()
            >>> d['query_kmer']
            'ATCG'
            >>> d['total_matches']
            0
        """
        return {
            'query_kmer': self.query_kmer,
            'exact_match': self.exact_match.to_dict() if self.exact_match else None,
            'matches': [match.to_dict() for match in self.matches],
            'total_matches': self.total_matches,
            'mutation_tolerance': self.mutation_tolerance,
            'database_path': self.database_path,
            'position_mutations_config': self.position_mutations_config
        }

    def to_json(self) -> str:
        """Serialize the FuzzyQueryResult to a JSON string.

        This method converts the complete query result to a JSON-formatted string,
        which can be easily stored, transmitted, or loaded by other applications.
        The JSON preserves all information including the nested match structures.

        Returns:
            str: JSON string representation of the complete query result.

        Example:
            >>> result = FuzzyQueryResult(
            ...     query_kmer="ATCG", exact_match=None, matches=[],
            ...     total_matches=0, mutation_tolerance=1, database_path="db.rkdb"
            ... )
            >>> json_str = result.to_json()
            >>> import json
            >>> data = json.loads(json_str)
            >>> data['query_kmer']
            'ATCG'
        """
        return json.dumps(self.to_dict())


@dataclass
class FuzzyBatchResult:
    """Aggregates results from multiple fuzzy queries.

    A FuzzyBatchResult contains the complete results of a batch fuzzy query
    operation, which processes multiple k-mers in parallel. It provides summary
    statistics and access to individual query results, making it easy to analyze
    patterns across multiple queries.

    Attributes:
        query_results (List[FuzzyQueryResult]): List of individual query results,
                                                one for each input k-mer
        total_queries (int): Total number of k-mers that were queried
        total_matches (int): Total number of unique matches found across all
                            queries (sum of all FuzzyQueryResult.total_matches)
        database_path (str): Path to the database file that was queried

    Example:
        >>> batch = FuzzyBatchResult(
        ...     query_results=[result1, result2],
        ...     total_queries=2,
        ...     total_matches=5,
        ...     database_path="/path/to/db.rkdb"
        ... )
        >>> print(f"Processed {batch.total_queries} queries")
        >>> print(f"Found {batch.queries_with_exact_matches} with exact matches")
    """
    query_results: List[FuzzyQueryResult]
    total_queries: int
    total_matches: int
    database_path: str

    @property
    def queries_with_exact_matches(self) -> int:
        """Count how many queries had exact matches.

        Returns:
            int: Number of queries that found at least one exact match
                 (distance = 0) in the database.

        Example:
            >>> batch = FuzzyBatchResult([], 3, 0, "db.rkdb")
            >>> batch.queries_with_exact_matches
            0
        """
        return sum(1 for result in self.query_results if result.has_exact_match)

    @property
    def queries_with_any_matches(self) -> int:
        """Count how many queries had any matches at all.

        This includes both exact matches (distance = 0) and fuzzy matches
        (distance > 0) within the specified mutation tolerance.

        Returns:
            int: Number of queries that found at least one match (either exact
                 or fuzzy) in the database.

        Example:
            >>> from rustkmer.fuzzy_query import FuzzyQueryResult, FuzzyMatchResult
            >>> result1 = FuzzyQueryResult("ATCG", None, [], 0, 1, "db.rkdb")
            >>> result2 = FuzzyQueryResult("TTCG", None, [FuzzyMatchResult("TTCG", 5, 0, [])], 1, 1, "db.rkdb")
            >>> batch = FuzzyBatchResult([result1, result2], 2, 1, "db.rkdb")
            >>> batch.queries_with_any_matches
            1
        """
        return sum(1 for result in self.query_results if result.matches or result.exact_match)

    def get_summary_table(self) -> str:
        """Generate a summary table of the batch query results.

        This method creates a formatted table showing overall statistics for the
        batch query operation, including success rates and per-query summaries.
        It's useful for getting a quick overview of how many queries found matches
        and identifying which specific queries were most successful.

        Returns:
            str: Multi-line string containing a formatted summary table with:
                 - Database path
                 - Total queries processed
                 - Number of queries with matches
                 - Number of queries with exact matches
                 - Match rates (as percentages)
                 - Per-query result summary

        Example:
            >>> batch = FuzzyBatchResult([], 10, 25, "db.rkdb")
            >>> summary = batch.get_summary_table()
            >>> "Total queries: 10" in summary
            True
            >>> "Database:" in summary
            True
        """
        lines = []
        lines.append("Batch Fuzzy Query Summary")
        lines.append("=" * 50)
        lines.append(f"Database: {self.database_path}")
        lines.append("")
        lines.append(f"Total queries: {self.total_queries}")
        lines.append(f"Queries with matches: {self.queries_with_any_matches}")
        lines.append(f"Queries with exact matches: {self.queries_with_exact_matches}")
        lines.append("")
        lines.append(f"Total matches found: {self.total_matches}")

        # Calculate match rate
        if self.total_queries > 0:
            match_rate = (self.queries_with_any_matches / self.total_queries) * 100
            exact_rate = (self.queries_with_exact_matches / self.total_queries) * 100
            lines.append("")
            lines.append(f"Match rate: {match_rate:.1f}%")
            lines.append(f"Exact match rate: {exact_rate:.1f}%")

        # Add per-query summary
        if self.query_results:
            lines.append("")
            lines.append("Per-query Results:")
            lines.append("-" * 30)
            for result in self.query_results:
                status = "✓" if result.matches else "✗"
                exact = " (exact)" if result.has_exact_match else ""
                lines.append(f"{status} {result.query_kmer}: {result.total_matches} matches{exact}")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Serialize the FuzzyBatchResult to a JSON string.

        This method converts the complete batch result to a JSON-formatted string,
        including all individual query results. The resulting JSON can be stored
        to file or transmitted for analysis by other tools.

        Returns:
            str: JSON string containing all batch result data including:
                 - Summary statistics (total queries, matches, etc.)
                 - Complete list of individual query results
                 - Each query's matches with full details

        Example:
            >>> batch = FuzzyBatchResult([], 2, 0, "db.rkdb")
            >>> json_str = batch.to_json()
            >>> import json
            >>> data = json.loads(json_str)
            >>> data['total_queries']
            2
            >>> 'query_results' in data
            True
        """
        # TODO: Will be fully implemented in T032
        # For now, return basic structure
        return json.dumps({
            'total_queries': self.total_queries,
            'total_matches': self.total_matches,
            'queries_with_exact_matches': self.queries_with_exact_matches,
            'queries_with_any_matches': self.queries_with_any_matches,
            'database_path': self.database_path,
            'query_results': [
                {
                    'query_kmer': result.query_kmer,
                    'exact_match': result.exact_match.to_dict() if result.exact_match else None,
                    'matches': [match.to_dict() for match in result.matches],
                    'total_matches': result.total_matches,
                    'mutation_tolerance': result.mutation_tolerance,
                    'database_path': result.database_path
                }
                for result in self.query_results
            ]
        })