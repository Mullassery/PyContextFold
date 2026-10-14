//! Reproducible benchmarks for the PyContextFold engine.
//!
//! Run with:
//!     cargo bench -p contextfold-bench
//!
//! Methodology: each benchmark folds an embedded fixture (see
//! `contextfold_bench::fixtures`) through the full pipeline using the standard
//! registry. Reduction ratios are computed from the same inputs and printed by
//! the `reduction` test-style benchmark so they can be reproduced.
//!
//! These numbers are environment-dependent; do not treat them as portable
//! performance guarantees.

use contextfold_bench::{fixtures, fold, synthesize};
use contextfold_parsers::standard_engine;
use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use std::time::Duration;

const PY_UNIT: &str = r#"
# comment for NAME
import os

def NAME(a, b):
    """Docstring for NAME."""
    # inner comment
    return a + b

class C_NAME:
    def method(self):
        return NAME(1, 2)
"#;

fn bench_fixtures(c: &mut Criterion) {
    let engine = standard_engine();
    let mut group = c.benchmark_group("fixtures/safe");
    group.warm_up_time(Duration::from_millis(300));
    group.measurement_time(Duration::from_millis(600));
    group.sample_size(10);
    for (name, path, src) in [
        ("python", "sample.py", fixtures::PYTHON),
        ("rust", "sample.rs", fixtures::RUST),
        ("typescript", "sample.ts", fixtures::TYPESCRIPT),
        ("go", "sample.go", fixtures::GO),
        ("markdown", "sample.md", fixtures::MARKDOWN),
        ("log", "sample.log", fixtures::LOG),
    ] {
        group.throughput(Throughput::Bytes(src.len() as u64));
        group.bench_with_input(BenchmarkId::from_parameter(name), &src, |b, src| {
            b.iter(|| fold(&engine, src, path, "safe"));
        });
    }
    group.finish();
}

fn bench_large_python(c: &mut Criterion) {
    let engine = standard_engine();
    let mut group = c.benchmark_group("large/python/safe");
    group.warm_up_time(Duration::from_millis(300));
    group.measurement_time(Duration::from_secs(2));
    group.sample_size(10);
    for n in [100usize, 1000] {
        let src = synthesize(PY_UNIT, n);
        group.throughput(Throughput::Bytes(src.len() as u64));
        group.bench_with_input(BenchmarkId::from_parameter(n), &src, |b, src| {
            b.iter(|| fold(&engine, src, "large.py", "safe"));
        });
    }
    group.finish();
}

fn bench_interface_only(c: &mut Criterion) {
    let engine = standard_engine();
    let src = synthesize(PY_UNIT, 1000);
    let mut group = c.benchmark_group("large/python/interface-only");
    group.warm_up_time(Duration::from_millis(300));
    group.measurement_time(Duration::from_secs(2));
    group.sample_size(10);
    group.throughput(Throughput::Bytes(src.len() as u64));
    group.bench_function("1000", |b| {
        b.iter(|| fold(&engine, &src, "large.py", "interface-only"));
    });
    group.finish();
}

criterion_group!(
    benches,
    bench_fixtures,
    bench_large_python,
    bench_interface_only
);
criterion_main!(benches);
