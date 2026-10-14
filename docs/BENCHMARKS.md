# Benchmarks

All numbers here are **reproducible** and **machine-dependent**. The reduction
ratios are stable (they are deterministic functions of the fixtures and
profiles); the timings are indicative only.

## Reproduce

```bash
# from the repository root
cargo bench -p contextfold-bench -- --noplot
```

The `--noplot` flag is recommended: criterion's default plotting backend is slow
and unnecessary for CI or quick runs. Reduction ratios can be reproduced with the
Python package:

```python
import pathlib, pycontextfold as pcf
for name in ["sample.py","sample.rs","sample.js","sample.ts","sample.go",
             "sample.md","sample.log","sample.json"]:
    src = (pathlib.Path("tests/fixtures")/name).read_text()
    prof = {"sample.md":"documentation","sample.log":"logs"}.get(name,"safe")
    r = pcf.fold(src, profile=prof, path=name)
    print(name, prof, f"{r.report.reduction_ratio*100:.1f}%")
```

## Reduction ratios

Measured on `tests/fixtures/*`, single pass, byte-based. `reduction_ratio` =
`1 - output_bytes / input_bytes`.

| Fixture | Profile | Input B | Output B | Reduction |
|---|---|---:|---:|---:|
| `sample.py` | safe | 615 | 495 | 19.5% |
| `sample.py` | interface-only | 615 | 561 | 8.8% |
| `sample.rs` | safe | 570 | 469 | 17.7% |
| `sample.js` | safe | 310 | 244 | 21.3% |
| `sample.ts` | safe | 355 | 299 | 15.8% |
| `sample.go` | safe | 325 | 265 | 18.5% |
| `sample.md` | documentation | 445 | 335 | 24.7% |
| `sample.log` | logs | 365 | 287 | 21.4% |
| `sample.json` | safe | 56 | 39 | 30.4% |

These fixtures are intentionally tiny and feature-dense, so the ratios are
modest. Reductions grow with real-world files that contain more comments,
docstrings, blank-line runs and repeated log/markdown lines.

## Throughput (indicative)

Environment: Apple Silicon (macOS/darwin), `cargo bench` release profile,
criterion with `--noplot`, warm-up 300 ms / measurement 600 ms–2 s. Treat these as
order-of-magnitude figures, not guarantees.

### Small fixtures (`safe`)

| Fixture | Time |
|---|---:|
| `sample.py` | ~120 µs |
| `sample.rs` | ~153 µs |
| `sample.ts` | ~84 µs |
| `sample.go` | ~88 µs |
| `sample.md` | ~2.4 µs |
| `sample.log` | ~1.1 µs |

### Large synthetic Python (`safe`, `NAME`-expanded functions)

| Functions | Bytes | Time | Throughput |
|---:|---:|---:|---:|
| 100 | ~19 KiB | ~5.0 ms | ~3.7 MiB/s |
| 1000 | ~190 KiB | ~54 ms | ~3.5 MiB/s |
| 1000 (`interface-only`) | ~190 KiB | ~41 ms | ~4.6 MiB/s |

The essentially constant MiB/s across sizes shows the pipeline is **linear** in
input size. (An earlier revision rebuilt a line index once per comment and
scanned protected ranges linearly, which made the 1000-function case ~395 ms and
superlinear; that was fixed with a cached line index and `O(log n)` interval
lookups — see `docs/ARCHITECTURE.md`.)

## Notes on interpretation

- Do **not** compare these timings across machines or to other tools as a
  benchmark claim. They exist to catch regressions in this repository.
- Reduction ratio measures **bytes**. It is not a token count. For token-based
  budgets, supply a `Tokenizer` and read `report.budget`.
- `interface-only` on a tiny file is only ~9% smaller because the file is mostly
  signatures and docstrings; on real files dominated by implementation bodies the
  reduction is much larger.
