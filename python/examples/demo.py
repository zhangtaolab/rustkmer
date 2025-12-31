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

db = Database(str(db_path), validate=False)
db_stats = db.stats()
print("Database stats:")
print(db_stats)
print("--------------------------------")

query_result1 = db.query("ACTAGTG")
print(query_result1)


query_result2 = db.query("TACCCCA")
print(query_result2)

print("--------------------------------")

print("Batch query result:")
batch_query_result = db.query_batch(["ACTAGTG","TACACAA","TACCCCA","TGAGCCA"])
print("Batch query results:")
for kmer, result in batch_query_result.items():
    print(f"  {kmer}: count={result.count}, canonical={result.canonical}, present={result.is_present}")

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

fuzzy_query_result2 = db.fuzzy_query("NNNNNTG")
print("Fuzzy query result for 'NNNNNTG'")
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

print("--------------------------------")

# Demonstrate position-specific mutations
print("Position-Specific Mutation Examples:")
print("=" * 50)

# Example 1: Single position mutation
print("\n1. Single position mutation (position 3 only):")
position_result1 = db.fuzzy_query("ACTAGTG", mutations=2, position_mutations="3:1")
print(f"  Query: ACTAGTG, position_mutations='3:1'")
print(f"  Has position mutations: {position_result1.has_position_mutations}")
print(f"  Total matches: {position_result1.total_matches}")
print(f"  Position groups: {position_result1.position_mutation_groups}")
print(f"  Positions used: {position_result1.get_mutation_positions_used()}")

# Example 2: Multiple positions in one group
print("\n2. Multiple positions in single group (positions 1,2,3 with max 2 mutations):")
position_result2 = db.fuzzy_query("ACTAGTG", mutations=2, position_mutations="1,2,3:2")
print(f"  Query: ACTAGTG, position_mutations='1,2,3:2'")
print(f"  Total matches: {position_result2.total_matches}")
print(f"  Position groups: {position_result2.position_mutation_groups}")
print(f"  Positions used: {position_result2.get_mutation_positions_used()}")

# Example 3: Range notation
print("\n3. Range notation (positions 2-4 with max 1 mutation):")
position_result3 = db.fuzzy_query("ACTAGTG", mutations=2, position_mutations="2-4:1")
print(f"  Query: ACTAGTG, position_mutations='2-4:1'")
print(f"  Total matches: {position_result3.total_matches}")
print(f"  Position groups: {position_result3.position_mutation_groups}")
print(f"  Positions used: {position_result3.get_mutation_positions_used()}")

# Example 4: Multiple independent groups
print("\n4. Multiple independent groups (positions 1,2:1 and 5,6:2):")
position_result4 = db.fuzzy_query("ACTAGTGAA", mutations=3, position_mutations="1,2:1;5,6:2")
print(f"  Query: ACTAGTGAA, position_mutations='1,2:1;5,6:2'")
print(f"  Total matches: {position_result4.total_matches}")
if position_result4.has_position_mutations:
    print(f"  Number of groups: {len(position_result4.position_mutation_groups)}")
    for i, group in enumerate(position_result4.position_mutation_groups):
        print(f"    Group {i+1}: positions {group['positions']}, max mutations {group['max_mutations']}")
    print(f"  All positions used: {position_result4.get_mutation_positions_used()}")

# Example 5: Compare global vs position mutations
print("\n5. Comparison: Global mutations vs Position mutations")
print("\n  Global mutations (up to 2 anywhere):")
global_result = db.fuzzy_query("ACTAGTG", mutations=2)
print(f"    Total matches: {global_result.total_matches}")

print("  Position mutations (up to 2 at positions 2,3,4 only):")
position_result5 = db.fuzzy_query("ACTAGTG", mutations=2, position_mutations="2,3,4:2")
print(f"    Total matches: {position_result5.total_matches}")
print(f"    Reduction ratio: {position_result5.total_matches}/{global_result.total_matches}")

# Example 6: Show detailed match analysis
print("\n6. Detailed match analysis with position mutations:")
if position_result2.matches:
    print("  Top 5 matches:")
    top_matches = position_result2.get_top_matches(5)
    for i, match in enumerate(top_matches, 1):
        print(f"    {i}. {match.kmer}")
        print(f"       Count: {match.count}")
        print(f"       Distance: {match.distance}")
        print(f"       Mutations: {match.mutations}")
        print(f"       Is exact match: {match.is_exact_match}")

# Example 7: Export position mutation results
print("\n7. Export position mutation results:")
result_dict = position_result2.to_dict()
print(f"  Result dictionary keys: {list(result_dict.keys())}")
print(f"  Position mutations config: {result_dict.get('position_mutations_config')}")

# Convert to JSON for further processing
import json
result_json = position_result2.to_json()
print(f"  JSON export length: {len(result_json)} characters")

# Example 8: Error handling demonstration
print("\n8. Error handling with position mutations:")
print("  Trying invalid position mutation format...")
try:
    invalid_result = db.fuzzy_query("ACTAGTG", mutations=1, position_mutations="invalid_format")
except Exception as e:
    print(f"    Caught error: {type(e).__name__}: {e}")

print("  Trying positions out of bounds...")
try:
    invalid_result = db.fuzzy_query("ACTAGTG", mutations=1, position_mutations="10:1")
except Exception as e:
    print(f"    Caught error: {type(e).__name__}: {e}")

print("  Trying mutation limit > position count...")
try:
    invalid_result = db.fuzzy_query("ACTAGTG", mutations=1, position_mutations="3,4:5")
except Exception as e:
    print(f"    Caught error: {type(e).__name__}: {e}")

print("\n" + "=" * 50)
print("Position-Specific Mutation Examples Completed!")

# Close the database
db.close()
print("\nDemo completed successfully!")