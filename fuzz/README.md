# Fuzzing

`cargo-fuzz` targets for PyContextFold. These live in a detached workspace so
they do not affect `cargo build --workspace` and do not require nightly for
normal development.

## Requirements

- Nightly Rust and [`cargo-fuzz`](https://github.com/rust-fuzz/cargo-fuzz):

```bash
cargo install cargo-fuzz
rustup toolchain install nightly
```

## Run

```bash
cargo +nightly fuzz run fold
```

The `fold` target feeds arbitrary UTF-8 through the whole pipeline for every
built-in profile and asserts the engine never panics and always yields a
deterministic report.

Regression inputs are written to `fuzz/artifacts/` and can be replayed with:

```bash
cargo +nightly fuzz run fold fuzz/artifacts/fold/<crash-file>
```
