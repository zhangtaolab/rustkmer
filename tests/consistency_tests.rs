//! Integration tests for consistency
//!
//! This file serves as the entry point for consistency tests

mod consistency;

#[test]
fn test_small_k_consistency_integration() {
    use crate::consistency::test_small_k::test_small_k_consistency;
    test_small_k_consistency();
}

#[test]
fn test_ambiguous_base_handling_integration() {
    use crate::consistency::test_ambiguous::test_ambiguous_base_handling;
    test_ambiguous_base_handling();
}

#[test]
fn test_canonical_representation_integration() {
    use crate::consistency::test_canonical::test_canonical_representation;
    test_canonical_representation();
}

#[test]
fn test_full_pipeline_consistency_integration() {
    use crate::consistency::test_full_pipeline::test_full_pipeline_consistency;
    test_full_pipeline_consistency();
}