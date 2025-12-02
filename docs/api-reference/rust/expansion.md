# Expansion

**Module**: `rustkmer::fuzzy::expansion`

## Overview

Query expansion and variant generation
This module handles the generation of concrete k-mer variants from fuzzy queries,
including wildcard expansion, mutation tolerance, and length normalization.

## API Reference

### Fns

#### generate_query_expansion

```rust
pub fn generate_query_expansion(query: &crate::fuzzy::FuzzyQuery) -> FuzzyResult<QueryExpansion> {
```

Generate query expansion from a fuzzy query

---

*Source: [`expansion.rs`](../../../fuzzy/expansion.rs)*