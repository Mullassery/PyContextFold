use contextfold_core::model::{FoldRequest, FoldResult, ParseStatus};

// Parsers exposes the standard engine (core + all analyzers).
use contextfold_parsers::standard_engine;

fn fold(path: &str, content: &str, profile: &str) -> FoldResult {
    let engine = standard_engine();
    let req = FoldRequest::new(content)
        .with_path(path)
        .with_profile(profile);
    engine.fold(req).expect("fold should succeed")
}

fn fixture(name: &str) -> &'static str {
    match name {
        "sample.py" => include_str!("../../../tests/fixtures/sample.py"),
        "sample.rs" => include_str!("../../../tests/fixtures/sample.rs"),
        "sample.js" => include_str!("../../../tests/fixtures/sample.js"),
        "sample.ts" => include_str!("../../../tests/fixtures/sample.ts"),
        "sample.go" => include_str!("../../../tests/fixtures/sample.go"),
        "sample.md" => include_str!("../../../tests/fixtures/sample.md"),
        "sample.log" => include_str!("../../../tests/fixtures/sample.log"),
        "sample.json" => include_str!("../../../tests/fixtures/sample.json"),
        "malformed.py" => include_str!("../../../tests/fixtures/malformed.py"),
        "protected.py" => include_str!("../../../tests/fixtures/protected.py"),
        "unicode.py" => include_str!("../../../tests/fixtures/unicode.py"),
        _ => panic!("unknown fixture {name}"),
    }
}

#[test]
fn python_safe_preserves_docstrings_and_imports_removes_comments() {
    let src = fixture("sample.py");
    let out = fold("sample.py", src, "safe");
    assert_eq!(out.report.detected_language, "python");
    assert_eq!(out.report.parse_status, ParseStatus::Parsed);
    assert!(out.report.syntax_valid == Some(true));
    assert!(out.report.behavior_preserving);
    // Docstrings are preserved by safe.
    assert!(out.output.contains("Module docstring"));
    // Comments are removed.
    assert!(!out
        .output
        .contains("A line comment that the safe profile removes"));
    assert!(!out.output.contains("inner comment"));
    // Imports survive.
    assert!(out.output.contains("import os"));
    assert!(out.output.contains("import sys"));
    // Executable statements survive.
    assert!(out.output.contains("return a + b"));
    assert!(out.output.contains("except Exception"));
}

#[test]
fn python_interface_only_elides_bodies_and_stays_valid() {
    let src = fixture("sample.py");
    let out = fold("sample.py", src, "interface-only");
    assert!(
        out.report.syntax_valid == Some(true),
        "output: {}",
        out.output
    );
    assert!(!out.report.behavior_preserving, "must be flagged lossy");
    assert!(out.output.contains("[contextfold: implementation omitted]"));
    assert!(!out.output.contains("return a + b"));
    // Imports retained (interface information).
    assert!(out.output.contains("import os"));
    // Class declaration retained.
    assert!(out.output.contains("class Greeter"));
}

#[test]
fn rust_safe_removes_comments_preserves_functions() {
    let src = fixture("sample.rs");
    let out = fold("sample.rs", src, "safe");
    assert_eq!(out.report.detected_language, "rust");
    assert!(out.report.syntax_valid == Some(true), "{}", out.output);
    assert!(!out.output.contains("// inner comment"));
    assert!(out.output.contains("pub fn add"));
    assert!(out.output.contains("use std::collections::HashMap"));
}

#[test]
fn javascript_typescript_go_remove_comments() {
    for (path, src) in [
        ("sample.js", fixture("sample.js")),
        ("sample.ts", fixture("sample.ts")),
        ("sample.go", fixture("sample.go")),
    ] {
        let out = fold(path, src, "safe");
        assert!(
            out.report.syntax_valid == Some(true),
            "{path} not valid: {}",
            out.output
        );
        assert!(
            !out.output.contains("inner comment"),
            "{path} still has inner comment"
        );
    }
}

#[test]
fn js_interface_only_elides_body() {
    let out = fold("sample.js", fixture("sample.js"), "interface-only");
    assert!(out.output.contains("[contextfold: implementation omitted]"));
    assert!(!out.output.contains("return a + b"));
}

#[test]
fn malformed_python_fails_safe() {
    let src = fixture("malformed.py");
    let out = fold("malformed.py", src, "safe");
    assert_eq!(out.report.parse_status, ParseStatus::ParseFailed);
    // Conservative fallback: content left byte-for-byte unchanged.
    assert_eq!(out.output, src);
    assert!(out.report.warnings.iter().any(|w| w.code == "parse_failed"));
}

#[test]
fn protected_marker_line_survives() {
    let src = fixture("protected.py");
    let out = fold("protected.py", src, "safe");
    assert!(out.output.contains("Protected banner: contextfold:keep"));
    assert!(out.output.contains("This second line has contextfold:keep"));
    assert!(!out.output.contains("removable comment"));
    assert!(out.report.protected_bytes > 0);
}

#[test]
fn unicode_is_handled() {
    let src = fixture("unicode.py");
    let out = fold("unicode.py", src, "safe");
    assert!(out.output.contains("héllo wörld 🌍 日本語"));
    assert!(out.report.syntax_valid == Some(true));
    assert!(!out.output.contains("коммент"));
}

#[test]
fn empty_input_is_handled() {
    let out = fold("empty.py", "", "safe");
    assert_eq!(out.output, "");
    assert_eq!(out.report.input.bytes, 0);
}

#[test]
fn markdown_documentation_profile_dedupes() {
    let src = fixture("sample.md");
    let out = fold("sample.md", src, "documentation");
    assert_eq!(out.report.detected_language, "markdown");
    // Fenced code content is preserved verbatim (including trailing spaces).
    assert!(out.output.contains("x = 1   "));
    // The duplicated intro paragraph is reduced.
    let count = out
        .output
        .matches("This is an introduction paragraph")
        .count();
    assert_eq!(count, 1, "dedupe should leave one copy: {}", out.output);
    // Normative bullet retained (both copies).
    assert!(out.output.contains("**must**"));
}

#[test]
fn logs_profile_collapses_repeats() {
    let src = fixture("sample.log");
    let out = fold("sample.log", src, "logs");
    assert_eq!(out.report.detected_language, "log");
    assert!(out.output.contains("collapsed"));
    assert!(!out.report.behavior_preserving);
    // Distinct events retained.
    assert!(out.output.contains("INFO done"));
    assert!(out.output.contains("id=10"));
    assert!(out.output.contains("id=11"));
}

#[test]
fn json_is_minified() {
    let src = fixture("sample.json");
    let out = fold("sample.json", src, "safe");
    assert_eq!(out.report.detected_language, "json");
    assert!(out.report.syntax_valid == Some(true));
    assert!(!out.output.contains(",   "));
}

#[test]
fn budget_is_reported_as_bytes_not_tokens() {
    let engine = standard_engine();
    let src = fixture("sample.py");
    let req = FoldRequest::new(src)
        .with_path("sample.py")
        .with_profile("safe")
        .with_budget(contextfold_core::Budget::bytes(10));
    let out = engine.fold(req).unwrap();
    let b = out.report.budget.unwrap();
    assert_eq!(b.metric, "bytes");
    assert!(!b.exact_tokens);
    assert!(!b.met, "a 10-byte budget should not be met");
}

#[test]
fn determinism_end_to_end() {
    let src = fixture("sample.py");
    let a = fold("sample.py", src, "safe");
    let b = fold("sample.py", src, "safe");
    assert_eq!(a.output, b.output);
    assert_eq!(a.report, b.report);
}

#[test]
fn unknown_format_is_left_unchanged() {
    let out = fold("blob.bin", "\u{0}\u{1}\u{2}binaryish\u{3}", "safe");
    assert_eq!(out.report.parse_status, ParseStatus::Unsupported);
    assert_eq!(out.output, "\u{0}\u{1}\u{2}binaryish\u{3}");
}
