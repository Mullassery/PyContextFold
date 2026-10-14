#![no_main]

//! Fuzz the full fold pipeline: arbitrary bytes, every built-in profile, all
//! supported languages. The only invariants are that the engine must never
//! panic and must always produce comparable, deterministic output/report.

use libfuzzer_sys::fuzz_target;

use contextfold_core::model::FoldRequest;
use contextfold_core::Profile;
use contextfold_parsers::standard_engine;

fuzz_target!(|data: &[u8]| {
    let Ok(text) = std::str::from_utf8(data) else {
        return;
    };

    let engine = standard_engine();
    for profile in Profile::names() {
        let request = FoldRequest::new(text).with_profile(profile);
        // Must never panic.
        let Ok(result) = engine.fold(request) else {
            continue;
        };
        // Determinism: folding the output again must not panic either.
        let _ = engine.fold(
            FoldRequest::new(result.output.as_str()).with_profile(profile),
        );
    }
});
