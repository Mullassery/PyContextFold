use contextfold_core::edit::{apply_edits, merge_spans, Edit};
use contextfold_core::lang::Span;
use contextfold_core::profile::Profile;
use contextfold_core::rules::RuleId;
use contextfold_core::transform::transform_text;
use proptest::prelude::*;

fn arb_text() -> impl Strategy<Value = String> {
    prop::collection::vec(
        prop_oneof![
            Just("hello".to_string()),
            Just("world  ".to_string()),
            Just("".to_string()),
            Just("  ".to_string()),
            Just("\ttab".to_string()),
            Just("unicode héllo 🌍".to_string()),
            Just("def f():".to_string()),
        ],
        0..40,
    )
    .prop_map(|lines| lines.join("\n"))
}

proptest! {
    #[test]
    fn transform_is_deterministic(text in arb_text()) {
        let p = Profile::named("safe").unwrap();
        let a = transform_text(&text, &p);
        let b = transform_text(&text, &p);
        prop_assert_eq!(a.text, b.text);
    }

    #[test]
    fn safe_text_output_has_no_trailing_hspace(text in arb_text()) {
        let p = Profile::named("safe").unwrap();
        let out = transform_text(&text, &p);
        for line in out.text.split('\n') {
            prop_assert!(!line.ends_with(' ') && !line.ends_with('\t'), "line {:?}", line);
        }
    }

    #[test]
    fn safe_text_output_has_no_long_blank_runs(text in arb_text()) {
        let p = Profile::named("safe").unwrap();
        let out = transform_text(&text, &p);
        prop_assert!(!out.text.contains("\n\n\n"));
    }

    #[test]
    fn apply_empty_edits_is_identity(text in arb_text()) {
        let out = apply_edits(&text, &[]);
        prop_assert_eq!(out.text, text);
    }

    #[test]
    fn apply_removing_whole_text_yields_empty(text in arb_text()) {
        if !text.is_empty() {
            let edits = vec![Edit::remove(Span::new(0, text.len()), RuleId::StripComments)];
            let out = apply_edits(&text, &edits);
            prop_assert_eq!(out.text, "");
        }
    }

    #[test]
    fn merge_spans_is_idempotent(spans in prop::collection::vec((0usize..200, 0usize..200), 0..30)) {
        let mut v: Vec<Span> = spans.into_iter().map(|(a, b)| {
            let (s, e) = if a <= b { (a, b) } else { (b, a) };
            Span::new(s, e)
        }).collect();
        let once = merge_spans(v.clone());
        v = once.clone();
        let twice = merge_spans(v);
        prop_assert_eq!(once, twice);
    }
}
