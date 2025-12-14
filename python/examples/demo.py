from rustkmer import Database
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use absolute path to test data
test_data_dir = Path(__file__).parent.parent / "tests" / "test_data"
db_path = test_data_dir / "tiny_test.rkdb"

if not db_path.exists():
    print(f"Error: Database file not found at {db_path}")
    print("Please ensure the test data exists.")
    sys.exit(1)

db = Database(str(db_path))
db_stats = db.stats()
print("Database stats:")
print(db_stats)
print("--------------------------------")

query_result1 = db.query("ACTAGTG")
print(query_result1)


query_result2 = db.query("TACCCCA")
print(query_result2)

print("--------------------------------")

fuzzy_query_result1 = db.fuzzy_query("ACTAGTG", mutations=2)
print("Fuzzy query result for 'ACTAGTG' with mutations=2:")
print(f"  Total matches found: {fuzzy_query_result1.total_matches}")
print(f"  Has exact match: {fuzzy_query_result1.has_exact_match}")
if fuzzy_query_result1.matches:
    print("  Matches found:")
    for i, match in enumerate(fuzzy_query_result1.matches[:10], 1):  # Show first 10 matches
        print(f"    {i}. {match.kmer} (count: {match.count}, distance: {match.distance})")
    if len(fuzzy_query_result1.matches) > 10:
        print(f"    ... and {len(fuzzy_query_result1.matches) - 10} more matches")
else:
    print("  No matches found")

print("--------------------------------")

fuzzy_query_result2 = db.fuzzy_query("ACTANTG")
print("Fuzzy query result for 'ACTANTG'")
print(f"  Total matches found: {fuzzy_query_result2.total_matches}")
print(f"  Has exact match: {fuzzy_query_result2.has_exact_match}")
if fuzzy_query_result2.matches:
    print("  Matches found:")
    for i, match in enumerate(fuzzy_query_result2.matches[:10], 1):  # Show first 10 matches
        print(f"    {i}. {match.kmer} (count: {match.count}, distance: {match.distance})")
    if len(fuzzy_query_result2.matches) > 10:
        print(f"    ... and {len(fuzzy_query_result2.matches) - 10} more matches")
else:
    print("  No matches found")