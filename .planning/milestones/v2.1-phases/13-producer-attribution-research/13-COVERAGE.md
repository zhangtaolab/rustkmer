# API Coverage — Phase 13 (Producer Attribution Research)

No external API integration: measurement-only research phase; the detected signal names rustkmer's internal profiling diagnostics API, not an external service.

Context: the `api-coverage.verify-pre` detector's `consumes` + `api` signal comes from
13-01-PLAN.md prose — "the k=31 source consumes the diagnostics API" — which names
rustkmer's own `#[cfg(feature = "profiling")]` diagnostics surface (`src/count/engine.rs`),
not a third-party API, SDK, REST/GraphQL endpoint, or service. No external surface is
integrated, wrapped, or consumed by this phase, and the phase explicitly forbids Rust
source changes.
