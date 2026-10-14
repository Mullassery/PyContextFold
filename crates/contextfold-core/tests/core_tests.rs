use contextfold_core::edit::{apply_edits, merge_spans, Edit, LineIndex, OffsetMap};
use contextfold_core::lang::Span;
use contextfold_core::profile::{BlankLineMode, Profile, ProfileOverrides, RuleOverrides};
use contextfold_core::rules::RuleId;
use contextfold_core::tokenizer::{Budget, Tokenizer};
use contextfold_core::transform::{
    transform_json, transform_log, transform_markdown, transform_text,
};

#[test]
fn apply_edits_removes_and_replaces() {
    let src = "abcdef";
    let edits = vec![
        Edit::remove(Span::new(1, 3), RuleId::StripComments), // remove "bc"
        Edit::replace(Span::new(4, 6), "XY", RuleId::InterfaceOnly), // "ef" -> "XY"
    ];
    let out = apply_edits(src, &edits);
    assert_eq!(out.text, "adXY");
    assert_eq!(out.applied, 2);
    assert_eq!(out.overlaps_dropped, 0);
}

#[test]
fn apply_edits_drops_overlaps_deterministically() {
    let src = "abcdef";
    let edits = vec![
        Edit::remove(Span::new(0, 4), RuleId::StripComments),
        Edit::remove(Span::new(2, 6), RuleId::StripComments),
    ];
    let out = apply_edits(src, &edits);
    // Earlier-starting edit wins.
    assert_eq!(out.text, "ef");
    assert_eq!(out.applied, 1);
    assert_eq!(out.overlaps_dropped, 1);
}

#[test]
fn apply_edits_identity_when_empty() {
    let src = "hello";
    let out = apply_edits(src, &[]);
    assert_eq!(out.text, "hello");
    assert_eq!(out.map.map(3), 3);
}

#[test]
fn offset_map_clamps_removed_regions() {
    let src = "abcdef";
    let edits = vec![Edit::remove(Span::new(1, 4), RuleId::StripComments)];
    let out = apply_edits(src, &edits);
    assert_eq!(out.text, "aef");
    // offsets inside the removed region clamp to the region start in output.
    assert_eq!(out.map.map(0), 0);
    assert_eq!(out.map.map(2), 1);
    assert_eq!(out.map.map(5), 2);
    assert_eq!(out.map.map_span(Span::new(4, 6)).start, out.map.map(4));
}

#[test]
fn merge_spans_merges_overlaps_and_adjacent() {
    let merged = merge_spans(vec![
        Span::new(0, 2),
        Span::new(2, 4),
        Span::new(6, 8),
        Span::new(7, 9),
    ]);
    assert_eq!(merged, vec![Span::new(0, 4), Span::new(6, 9)]);
}

#[test]
fn line_index_basic() {
    let src = "a\nbb\n\nccc";
    let idx = LineIndex::new(src);
    assert_eq!(idx.len(), 4);
    assert_eq!(idx.content(0), Some("a"));
    assert_eq!(idx.content(1), Some("bb"));
    assert!(idx.is_blank(2));
    assert_eq!(idx.content(3), Some("ccc"));
    assert_eq!(idx.line_of(0), Some(0));
    assert_eq!(idx.line_of(6), Some(3));
}

#[test]
fn profile_names_and_versions() {
    let names = Profile::names();
    assert!(names.contains(&"safe"));
    assert!(names.contains(&"interface-only"));
    for n in names {
        let p = Profile::named(n).unwrap();
        assert_eq!(p.name, *n);
        assert_eq!(p.version, contextfold_core::PROFILE_SCHEMA_VERSION);
    }
    assert!(Profile::named("does-not-exist").is_err());
}

#[test]
fn profile_overrides_apply() {
    let ov = ProfileOverrides {
        rules: Some(RuleOverrides {
            blank_lines: Some(BlankLineMode::RemoveAll),
            ..Default::default()
        }),
        allow_lossy: Some(true),
        ..Default::default()
    };
    let p = Profile::named_with_overrides("safe", ov).unwrap();
    assert_eq!(p.rules.blank_lines, BlankLineMode::RemoveAll);
    assert!(p.loss.allow_lossy);
}

#[test]
fn safe_profile_metadata_is_not_lossy() {
    let p = Profile::named("safe").unwrap();
    assert!(!p.loss.allow_lossy);
    assert!(!p.rules.interface_only);
    assert!(!p.rules.docstrings);
}

#[test]
fn json_minifies_and_is_stable() {
    let p = Profile::named("safe").unwrap();
    let src = "{ \"a\" : 1 ,   \"b\" : [ 1, 2 ] }";
    let out = transform_json(src, &p);
    assert_eq!(out.text, r#"{"a":1,"b":[1,2]}"#);
}

#[test]
fn json_invalid_is_left_alone_with_warning() {
    let p = Profile::named("safe").unwrap();
    let src = "{ not json   ";
    let out = transform_json(src, &p);
    assert!(out.warnings.iter().any(|w| w.code == "json_invalid"));
    assert!(out.text.contains("not json"));
}

#[test]
fn text_fallback_trims_and_collapses() {
    let p = Profile::named("safe").unwrap();
    let src = "hello   \n\n\n\nworld\t\n";
    let out = transform_text(src, &p);
    assert!(!out.text.contains("   \n"));
    assert!(!out.text.contains("\n\n\n"));
}

#[test]
fn markdown_preserves_code_fences() {
    let p = Profile::named("documentation").unwrap();
    let src = "para\n\n\n```\ncode with trailing   \n\n\nmore\n```\nafter\n";
    let out = transform_markdown(src, &p);
    assert!(
        out.text.contains("code with trailing   "),
        "fence preserved: {:?}",
        out.text
    );
    assert!(out.text.contains("```"));
}

#[test]
fn markdown_dedupe_removes_adjacent_duplicates() {
    let p = Profile::named("documentation").unwrap();
    let src = "same line\nsame line\nsame line\n";
    let out = transform_markdown(src, &p);
    assert_eq!(out.text, "same line\n");
}

#[test]
fn markdown_dedupe_keeps_normative_and_headings() {
    let p = Profile::named("documentation").unwrap();
    let src = "# Heading\n# Heading\nYou must do X\nYou must do X\n";
    let out = transform_markdown(src, &p);
    assert!(out.text.contains("# Heading\n# Heading"));
    assert!(out.text.matches("You must do X").count() == 2);
}

#[test]
fn logs_collapse_consecutive_duplicates() {
    let p = Profile::named("logs").unwrap();
    let src = "2024-01-01T00:00:00 INFO a\n2024-01-01T00:00:01 INFO a\n2024-01-01T00:00:02 INFO a\n2024-01-01T00:00:03 INFO b\n";
    let out = transform_log(src, &p);
    assert!(out.text.contains("collapsed"), "{}", out.text);
    // The distinct event must remain.
    assert!(out.text.contains("INFO b"));
    // One representative 'a' retained.
    assert_eq!(out.text.matches("INFO a").count(), 1);
}

#[test]
fn logs_do_not_merge_distinct_events() {
    let p = Profile::named("logs").unwrap();
    let src = "INFO a\nINFO b\nINFO a\n";
    let out = transform_log(src, &p);
    assert!(!out.text.contains("collapsed"));
}

#[derive(Clone)]
struct ByteTokenizer;
impl Tokenizer for ByteTokenizer {
    fn name(&self) -> &str {
        "byte-tok"
    }
    fn count(&self, text: &str) -> u64 {
        text.len() as u64
    }
}

#[test]
fn budget_measurement_uses_exact_metric() {
    let b = Budget::bytes(10);
    assert_eq!(b.measure("hello").unwrap(), 5);
    let c = Budget::characters(10);
    assert_eq!(c.measure("héllo").unwrap(), 5);
    let t = Budget::tokens(10, ByteTokenizer);
    assert_eq!(t.measure("héllo").unwrap(), 6); // utf-8 bytes
}

#[test]
fn offset_map_exported_from_edit_module() {
    // OffsetMap is usable directly (public API surface).
    fn _takes(m: &OffsetMap) -> usize {
        m.map(0)
    }
    let out = apply_edits("abc", &[]);
    assert_eq!(_takes(&out.map), 0);
}
