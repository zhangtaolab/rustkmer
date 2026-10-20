<!--
  Raw output of `cargo test --test golden_sha256_tests` with the dense widening
  mutated in src/hash/table.rs::get_all_counts from `*r.key() as u128` to
  `*r.key() as u128 ^ (1u128 << 96)`. Committed as the RED evidence for plan
  03-08 Task 1 step 6. The mutation was reverted from the committed state
  (`git checkout -- src/hash/table.rs`) immediately after this run.
-->

```text
    Finished `test` profile [unoptimized + debuginfo] target(s) in 0.11s
     Running tests/golden_sha256_tests.rs (target/debug/deps/golden_sha256_tests-1bfe7a3e521163e6)

running 5 tests
test golden_manifest_covers_every_fixture_this_binary_checks ... ok
test dense_write_path_bytes_match_a_hand_built_reference ... FAILED
test write_read_write_is_byte_idempotent ... ok
test dense_k32_high_bytes_are_zero_on_disk ... FAILED
test golden_rkdb_sha256_unchanged_post_dense ... ok

failures:

---- dense_write_path_bytes_match_a_hand_built_reference stdout ----

thread 'dense_write_path_bytes_match_a_hand_built_reference' (1898332) panicked at tests/golden_sha256_tests.rs:380:5:
first difference at data-section byte 12: production arm 0x01, test-built reference 0x00 (production arm 160 bytes, reference 160 bytes)
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace

---- dense_k32_high_bytes_are_zero_on_disk stdout ----

thread 'dense_k32_high_bytes_are_zero_on_disk' (1898331) panicked at tests/golden_sha256_tests.rs:469:5:
assertion `left == right` failed: the high 8 bytes must be all zero on disk — this is the u64 -> u128 zero-extension, observed in the file rather than asserted about the code
  left: [0, 0, 0, 0, 1, 0, 0, 0]
 right: [0, 0, 0, 0, 0, 0, 0, 0]


failures:
    dense_k32_high_bytes_are_zero_on_disk
    dense_write_path_bytes_match_a_hand_built_reference

test result: FAILED. 3 passed; 2 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

error: test failed, to rerun pass `--test golden_sha256_tests`
```
