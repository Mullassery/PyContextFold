//! Shared helpers for PyContextFold benchmarks.

use contextfold_core::model::FoldRequest;
use contextfold_core::Engine;

/// Fixture sources embedded at compile time (kept in sync with `tests/fixtures`).
pub mod fixtures {
    pub const PYTHON: &str = include_str!("../../../tests/fixtures/sample.py");
    pub const RUST: &str = include_str!("../../../tests/fixtures/sample.rs");
    pub const TYPESCRIPT: &str = include_str!("../../../tests/fixtures/sample.ts");
    pub const GO: &str = include_str!("../../../tests/fixtures/sample.go");
    pub const MARKDOWN: &str = include_str!("../../../tests/fixtures/sample.md");
    pub const LOG: &str = include_str!("../../../tests/fixtures/sample.log");
}

/// Build a synthetic, large source file by repeating `unit` `n` times with
/// distinct indices so the parser cannot trivially collapse it.
pub fn synthesize(unit: &str, n: usize) -> String {
    let mut out = String::with_capacity(unit.len() * n);
    for i in 0..n {
        out.push_str(&unit.replace("NAME", &format!("name_{i}")));
    }
    out
}

pub fn fold(
    engine: &Engine,
    content: &str,
    path: &str,
    profile: &str,
) -> contextfold_core::FoldResult {
    let req = FoldRequest::new(content)
        .with_path(path)
        .with_profile(profile);
    engine.fold(req).expect("fold")
}
