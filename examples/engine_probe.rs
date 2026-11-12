//! Producer/worker timing probe for the shared counting engine (07-04).
//!
//! The diagnostics are compiled in only with the `profiling` feature, so this
//! example is the one place that reads them. Build and run:
//!
//! ```text
//! cargo build --release --locked --features profiling --example engine_probe
//! target/release/examples/engine_probe <input-path> <fasta|fastq> <threads>
//! ```
//!
//! The probe counts one file with k = 21 canonical, calls `finish`, and prints
//! one JSON object with `input`, `threads`, `wall_nanos`, `producer_nanos`, and
//! per-worker `batches`/`busy_nanos`. Without the feature it prints a hint to
//! stderr, no JSON, and exits 2.

#[cfg(feature = "profiling")]
fn main() -> std::process::ExitCode {
    use std::path::PathBuf;

    use rustkmer::count::{CountEngine, EngineConfig, SequenceKind};

    let arguments: Vec<String> = std::env::args().collect();
    if arguments.len() != 4 {
        eprintln!("usage: engine_probe <input-path> <fasta|fastq> <threads>");
        return std::process::ExitCode::from(2);
    }

    let input = PathBuf::from(&arguments[1]);
    let kind = match arguments[2].as_str() {
        "fasta" => SequenceKind::Fasta,
        "fastq" => SequenceKind::Fastq,
        other => {
            eprintln!("engine_probe: unsupported format {other:?} (expected fasta|fastq)");
            return std::process::ExitCode::from(2);
        }
    };
    let threads = match arguments[3].parse::<usize>() {
        Ok(threads) if threads >= 1 => threads,
        _ => {
            eprintln!("engine_probe: threads must be a positive integer");
            return std::process::ExitCode::from(2);
        }
    };

    let config = EngineConfig::new(21, true, threads, 1_000_000);
    let mut engine = match CountEngine::new(config) {
        Ok(engine) => engine,
        Err(error) => {
            eprintln!("engine_probe: failed to build the counting engine: {error}");
            return std::process::ExitCode::from(2);
        }
    };
    if let Err(error) = engine.count_file(&input, kind) {
        eprintln!("engine_probe: counting failed: {error}");
        return std::process::ExitCode::from(2);
    }
    let result = match engine.finish() {
        Ok(result) => result,
        Err(error) => {
            eprintln!("engine_probe: finish failed: {error}");
            return std::process::ExitCode::from(2);
        }
    };

    let Some(diagnostics) = result.diagnostics() else {
        eprintln!("engine_probe: diagnostics unavailable from the finished result");
        return std::process::ExitCode::from(2);
    };
    let workers: Vec<serde_json::Value> = diagnostics
        .workers
        .iter()
        .map(|worker| {
            serde_json::json!({
                "batches": worker.batches,
                "busy_nanos": worker.busy_nanos,
            })
        })
        .collect();
    let document = serde_json::json!({
        "input": input.display().to_string(),
        "threads": threads,
        "wall_nanos": diagnostics.wall_nanos,
        "producer_nanos": diagnostics.producer_nanos,
        "workers": workers,
    });
    println!("{document}");
    std::process::ExitCode::SUCCESS
}

#[cfg(not(feature = "profiling"))]
fn main() -> std::process::ExitCode {
    eprintln!(
        "engine_probe: build with `cargo build --release --locked --features profiling \
         --example engine_probe` to enable diagnostics"
    );
    std::process::ExitCode::from(2)
}
