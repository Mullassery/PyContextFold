use crate::analyzer::{Analysis, LanguageAnalyzer};
use crate::edit::{apply_edits, merge_spans, overlaps_sorted, Edit, LineIndex};
use crate::lang::{LanguageId, Span};
use crate::model::Warning;
use crate::profile::{BlankLineMode, CommentMode, Profile};
use crate::rules::{RuleId, RuleRecord};

/// The outcome of the transformation stage (before validation/report assembly).
#[derive(Debug, Clone)]
pub struct TransformOutcome {
    pub text: String,
    pub records: Vec<RuleRecord>,
    pub warnings: Vec<Warning>,
    pub protected_bytes: usize,
}

impl TransformOutcome {
    fn noop(text: &str) -> Self {
        TransformOutcome {
            text: text.to_string(),
            records: Vec::new(),
            warnings: Vec::new(),
            protected_bytes: 0,
        }
    }
}

/// Compute the hard-protected spans for the *original* source: caller-supplied
/// ranges plus whole lines containing any configured marker substring.
pub fn hard_protected(source: &str, profile: &Profile) -> Vec<Span> {
    let mut spans = profile.preservation.protected_ranges.clone();
    if !profile.preservation.protected_line_markers.is_empty() {
        let index = LineIndex::new(source);
        for i in 0..index.len() {
            if let Some(line) = index.content(i) {
                if profile
                    .preservation
                    .protected_line_markers
                    .iter()
                    .any(|m| !m.is_empty() && line.contains(m.as_str()))
                {
                    if let Some(f) = index.full_span(i) {
                        spans.push(f);
                    }
                }
            }
        }
    }
    merge_spans(spans)
}

fn removable_span(index: &LineIndex, source: &str, span: Span) -> Span {
    whole_line_removal(index, source, span).unwrap_or(span)
}

/// If the span's lines contain nothing but the span plus whitespace, return a
/// span covering the full line(s) (including trailing newline).
fn whole_line_removal(index: &LineIndex, source: &str, span: Span) -> Option<Span> {
    if span.is_empty() || span.end > source.len() {
        return None;
    }
    if !source.is_char_boundary(span.start) || !source.is_char_boundary(span.end) {
        return None;
    }
    let first = index.line_of(span.start)?;
    let last = index.line_of(span.end.saturating_sub(1).max(span.start))?;
    let fs = index.content_span(first)?;
    if !source[fs.start..span.start].chars().all(is_hspace) {
        return None;
    }
    let ls = index.content_span(last)?;
    if span.end < ls.end && !source[span.end..ls.end].chars().all(is_hspace) {
        return None;
    }
    Some(Span::new(fs.start, index.full_span(last)?.end))
}

fn is_hspace(c: char) -> bool {
    c == ' ' || c == '\t'
}

fn is_multiline(s: Span, source: &str) -> bool {
    source[s.start..s.end].contains('\n')
}

/// True when `content` is contained in one of the (pre-sorted, merged)
/// multiline string spans. `multiline` must be sorted by start and disjoint.
fn line_in_multiline_sorted(content: Span, multiline: &[Span]) -> bool {
    if multiline.is_empty() {
        return false;
    }
    let idx = multiline.partition_point(|s| s.start <= content.start);
    if idx == 0 {
        return false;
    }
    let s = multiline[idx - 1];
    s.contains(content)
}

/// Filter `string_spans` down to multiline spans, sorted and merged so that
/// [`line_in_multiline_sorted`] can binary-search them.
fn multiline_index(string_spans: &[Span], source: &str) -> Vec<Span> {
    let multi: Vec<Span> = string_spans
        .iter()
        .copied()
        .filter(|s| !s.is_empty() && s.end <= source.len() && is_multiline(*s, source))
        .collect();
    merge_spans(multi)
}

fn trim_trailing_edits(
    source: &str,
    protected: &[Span],
    string_spans: &[Span],
    hard_break_aware: bool,
    skip_blank: bool,
) -> Vec<Edit> {
    let index = LineIndex::new(source);
    let protected = merge_spans(protected.to_vec());
    let multiline = multiline_index(string_spans, source);
    let mut edits = Vec::new();
    for i in 0..index.len() {
        let content = match index.content_span(i) {
            Some(c) => c,
            None => continue,
        };
        if overlaps_sorted(content, &protected) {
            continue;
        }
        if line_in_multiline_sorted(content, &multiline) {
            continue;
        }
        let line = &source[content.start..content.end];
        if line.is_empty() {
            continue;
        }
        if skip_blank && line.chars().all(is_hspace) {
            continue;
        }
        let trimmed = line.trim_end_matches(is_hspace);
        if trimmed.len() == line.len() {
            continue;
        }
        if hard_break_aware {
            // Preserve Markdown hard line breaks (2+ trailing spaces).
            let trail = &line[trimmed.len()..];
            if trail.len() >= 2 {
                continue;
            }
        }
        let start = content.start + trimmed.len();
        edits.push(Edit::remove(
            Span::new(start, content.end),
            RuleId::TrimTrailingWhitespace,
        ));
    }
    edits
}

fn blank_line_edits(
    source: &str,
    mode: BlankLineMode,
    protected: &[Span],
    string_spans: &[Span],
) -> Vec<Edit> {
    if mode == BlankLineMode::Keep {
        return Vec::new();
    }
    let index = LineIndex::new(source);
    let protected = merge_spans(protected.to_vec());
    let multiline = multiline_index(string_spans, source);
    let eligible = |i: usize| -> bool {
        match index.content_span(i) {
            Some(c) => !overlaps_sorted(c, &protected) && !line_in_multiline_sorted(c, &multiline),
            None => false,
        }
    };
    let mut edits = Vec::new();
    let mut i = 0usize;
    while i < index.len() {
        if !index.is_blank(i) || !eligible(i) {
            i += 1;
            continue;
        }
        let run_start = i;
        while i < index.len() && index.is_blank(i) && eligible(i) {
            i += 1;
        }
        let run_len = i - run_start;
        match mode {
            BlankLineMode::Keep => {}
            BlankLineMode::CollapseToOne => {
                if run_len > 1 {
                    let start = index.full_span(run_start + 1).unwrap().start;
                    let end = index.full_span(i - 1).unwrap().end;
                    edits.push(Edit::remove(
                        Span::new(start, end),
                        RuleId::CollapseBlankLines,
                    ));
                }
                // Normalise the retained blank line (strip stray spaces/tabs).
                if let Some(c) = index.content_span(run_start) {
                    if !c.is_empty() {
                        edits.push(Edit::remove(c, RuleId::TrimTrailingWhitespace));
                    }
                }
            }
            BlankLineMode::RemoveAll => {
                let start = index.full_span(run_start).unwrap().start;
                let end = index.full_span(i - 1).unwrap().end;
                edits.push(Edit::remove(
                    Span::new(start, end),
                    RuleId::CollapseBlankLines,
                ));
            }
        }
    }
    edits
}

fn placeholder_for(language: LanguageId) -> &'static str {
    match language {
        LanguageId::Python => "...  # [contextfold: implementation omitted]",
        _ => "{ /* [contextfold: implementation omitted] */ }",
    }
}

fn body_is_empty(source: &str, body: Span) -> bool {
    source[body.start..body.end]
        .chars()
        .all(|c| c == '{' || c == '}' || c == ';' || c.is_whitespace())
}

/// The full code transformation pipeline (structural edits then a whitespace
/// pass on the intermediate text).
pub fn transform_code(
    source: &str,
    analysis: &Analysis,
    analyzer: &dyn LanguageAnalyzer,
    profile: &Profile,
) -> TransformOutcome {
    let hard = hard_protected(source, profile);
    let protected_bytes: usize = hard.iter().map(|s| s.len()).sum();
    let language = analysis.language;
    let rules = &profile.rules;
    let mut warnings = Vec::new();

    if !analysis.parsed {
        warnings.push(Warning::new(
            "parse_failed",
            "input did not parse cleanly; no transformations were applied (conservative fallback)",
        ));
        let mut out = TransformOutcome::noop(source);
        out.warnings = warnings;
        out.protected_bytes = protected_bytes;
        return out;
    }

    let mut struct_edits: Vec<Edit> = Vec::new();
    let line_index = LineIndex::new(source);

    if rules.comments == CommentMode::Remove {
        for c in &analysis.comment_spans {
            if overlaps_sorted(*c, &hard) {
                continue;
            }
            struct_edits.push(Edit::remove(
                removable_span(&line_index, source, *c),
                RuleId::StripComments,
            ));
        }
    }

    if rules.docstrings {
        for d in &analysis.docstring_spans {
            if overlaps_sorted(*d, &hard) {
                continue;
            }
            struct_edits.push(Edit::remove(
                removable_span(&line_index, source, *d),
                RuleId::StripDocstrings,
            ));
        }
    }

    if rules.interface_only {
        if profile.loss.allow_lossy {
            let placeholder = placeholder_for(language);
            let error_spans = merge_spans(analysis.error_handling_spans.clone());
            for decl in &analysis.declarations {
                if !decl.has_body {
                    continue;
                }
                let body = Span::new(decl.body_start, decl.body_end);
                if body.is_empty() || body.end > source.len() {
                    continue;
                }
                if overlaps_sorted(body, &hard) {
                    continue;
                }
                if profile.preservation.protect_error_handling
                    && overlaps_sorted(body, &error_spans)
                {
                    continue;
                }
                if body_is_empty(source, body) {
                    continue;
                }
                struct_edits.push(Edit::replace(body, placeholder, RuleId::InterfaceOnly));
            }
        } else {
            warnings.push(Warning::new(
                "lossy_rule_blocked",
                "interface_only requested but loss policy does not allow lossy transformations",
            ));
        }
    }

    let struct_outcome = apply_edits(source, &struct_edits);
    let text1 = struct_outcome.text;
    let map = struct_outcome.map;

    let (string_spans, mapped_protected): (Vec<Span>, Vec<Span>) = if text1 == source {
        (analysis.string_spans.clone(), hard.clone())
    } else {
        let a1 = analyzer.analyze(&text1);
        let mapped = hard.iter().map(|s| map.map_span(*s)).collect();
        (a1.string_spans, mapped)
    };

    let skip_blank = rules.blank_lines != BlankLineMode::Keep;
    let mut ws_edits =
        trim_trailing_edits(&text1, &mapped_protected, &string_spans, false, skip_blank);
    ws_edits.extend(blank_line_edits(
        &text1,
        rules.blank_lines,
        &mapped_protected,
        &string_spans,
    ));

    let final_text = if ws_edits.is_empty() {
        text1
    } else {
        apply_edits(&text1, &ws_edits).text
    };

    let records = build_records(&struct_edits, &ws_edits);

    TransformOutcome {
        text: final_text,
        records,
        warnings,
        protected_bytes,
    }
}

fn build_records(struct_edits: &[Edit], ws_edits: &[Edit]) -> Vec<RuleRecord> {
    let mut order: Vec<RuleId> = Vec::new();
    let mut counts: Vec<(RuleId, usize, i64)> = Vec::new();
    for e in struct_edits.iter().chain(ws_edits.iter()) {
        if let Some(entry) = counts.iter_mut().find(|(r, _, _)| *r == e.rule) {
            entry.1 += 1;
            entry.2 += e.span.len() as i64 - e.replacement.len() as i64;
        } else {
            order.push(e.rule);
            counts.push((e.rule, 1, e.span.len() as i64 - e.replacement.len() as i64));
        }
    }
    order
        .into_iter()
        .map(|rule| {
            let (_, c, d) = counts.iter().find(|(r, _, _)| *r == rule).unwrap();
            RuleRecord::new(rule, *c, *d)
        })
        .collect()
}

/// Markdown handling: whitespace normalisation plus optional dedupe.
pub fn transform_markdown(source: &str, profile: &Profile) -> TransformOutcome {
    let protected = hard_protected(source, profile);
    let protected_bytes: usize = protected.iter().map(|s| s.len()).sum();
    let fences = markdown_fence_spans(source);

    let mut edits = trim_trailing_edits(
        source,
        &protected,
        &fences,
        true,
        profile.rules.blank_lines != BlankLineMode::Keep,
    );
    edits.extend(blank_line_edits(
        source,
        profile.rules.blank_lines,
        &protected,
        &fences,
    ));
    if profile.rules.markdown_dedupe {
        edits.extend(markdown_dedupe_edits(source, &protected, &fences));
    }

    if edits.is_empty() {
        let mut out = TransformOutcome::noop(source);
        out.protected_bytes = protected_bytes;
        return out;
    }
    let records = record_from_edits(&edits);
    let out = apply_edits(source, &edits).text;
    TransformOutcome {
        text: out,
        records,
        warnings: Vec::new(),
        protected_bytes,
    }
}

fn markdown_fence_spans(source: &str) -> Vec<Span> {
    let index = LineIndex::new(source);
    let mut spans = Vec::new();
    let mut open: Option<(usize, char, usize)> = None;
    for i in 0..index.len() {
        let line = index.content(i).unwrap_or("");
        let trimmed = line.trim_start();
        let Some(marker) = trimmed.chars().next() else {
            continue;
        };
        if marker != '`' && marker != '~' {
            continue;
        }
        let count = trimmed.chars().take_while(|c| *c == marker).count();
        if count < 3 {
            continue;
        }
        match open {
            None => open = Some((i, marker, count)),
            Some((start, m0, count0)) => {
                if marker == m0 && (count >= count0 || count >= 3) {
                    let s = index.full_span(start).unwrap().start;
                    let e = index.full_span(i).unwrap().end;
                    spans.push(Span::new(s, e));
                    open = None;
                }
            }
        }
    }
    if let Some((start, _, _)) = open {
        let s = index.full_span(start).unwrap().start;
        spans.push(Span::new(s, source.len()));
    }
    merge_spans(spans)
}

fn markdown_dedupe_edits(source: &str, protected: &[Span], fences: &[Span]) -> Vec<Edit> {
    let index = LineIndex::new(source);
    let protected = merge_spans(protected.to_vec());
    let fences = merge_spans(fences.to_vec());
    let mut edits = Vec::new();
    let mut prev_kept: Option<String> = None;
    for i in 0..index.len() {
        let content = match index.content_span(i) {
            Some(c) => c,
            None => continue,
        };
        if overlaps_sorted(content, &protected) || overlaps_sorted(content, &fences) {
            prev_kept = None;
            continue;
        }
        if index.is_blank(i) {
            prev_kept = None;
            continue;
        }
        let line = &source[content.start..content.end];
        let trimmed = line.trim();
        if !dedupe_candidate(trimmed) {
            prev_kept = None;
            continue;
        }
        if let Some(prev) = &prev_kept {
            if prev == trimmed {
                edits.push(Edit::remove(
                    Span::new(content.start, index.full_span(i).unwrap().end),
                    RuleId::MarkdownDedupe,
                ));
                continue;
            }
        }
        prev_kept = Some(trimmed.to_string());
    }
    edits
}

fn dedupe_candidate(trimmed: &str) -> bool {
    if trimmed.is_empty()
        || trimmed.starts_with('#')
        || trimmed.starts_with("```")
        || trimmed.starts_with("~~~")
    {
        return false;
    }
    if trimmed.contains("](") || trimmed.contains("http://") || trimmed.contains("https://") {
        return false;
    }
    let lower = trimmed.to_ascii_lowercase();
    const NORMATIVE: [&str; 10] = [
        "must",
        "shall",
        "require",
        "note:",
        "warning",
        "caution",
        "important",
        "deprecated",
        "see:",
        "references",
    ];
    !NORMATIVE
        .iter()
        .any(|k| lower.starts_with(k) || lower.contains(&format!(" {k}")))
}

/// Plain-text conservative fallback: whitespace normalisation only.
pub fn transform_text(source: &str, profile: &Profile) -> TransformOutcome {
    let protected = hard_protected(source, profile);
    let protected_bytes: usize = protected.iter().map(|s| s.len()).sum();
    let skip_blank = profile.rules.blank_lines != BlankLineMode::Keep;
    let mut edits = trim_trailing_edits(source, &protected, &[], false, skip_blank);
    edits.extend(blank_line_edits(
        source,
        profile.rules.blank_lines,
        &protected,
        &[],
    ));
    if edits.is_empty() {
        let mut out = TransformOutcome::noop(source);
        out.protected_bytes = protected_bytes;
        return out;
    }
    let records = record_from_edits(&edits);
    let out = apply_edits(source, &edits).text;
    TransformOutcome {
        text: out,
        records,
        warnings: Vec::new(),
        protected_bytes,
    }
}

/// JSON: parse and re-serialise compactly. Structurally conservative; invalid
/// JSON is left untouched (with whitespace normalisation only) and warned.
pub fn transform_json(source: &str, profile: &Profile) -> TransformOutcome {
    let protected = hard_protected(source, profile);
    let protected_bytes: usize = protected.iter().map(|s| s.len()).sum();
    match serde_json::from_str::<serde_json::Value>(source) {
        Ok(value) => {
            let compact = serde_json::to_string(&value).unwrap_or_else(|_| source.to_string());
            if compact.len() >= source.len() {
                let mut out = TransformOutcome::noop(source);
                out.protected_bytes = protected_bytes;
                return out;
            }
            let delta = compact.len() as i64 - source.len() as i64;
            TransformOutcome {
                text: compact,
                records: vec![RuleRecord::new(RuleId::TrimTrailingWhitespace, 1, delta)],
                warnings: Vec::new(),
                protected_bytes,
            }
        }
        Err(_) => {
            let mut out = TransformOutcome::noop(source);
            out.warnings.push(Warning::new(
                "json_invalid",
                "input is not valid JSON; whitespace-only fallback applied",
            ));
            let skip_blank = profile.rules.blank_lines != BlankLineMode::Keep;
            let mut edits = trim_trailing_edits(source, &protected, &[], false, skip_blank);
            edits.extend(blank_line_edits(
                source,
                profile.rules.blank_lines,
                &protected,
                &[],
            ));
            if !edits.is_empty() {
                out.records = record_from_edits(&edits);
                out.text = apply_edits(source, &edits).text;
            }
            out.protected_bytes = protected_bytes;
            out
        }
    }
}

/// Log handling: collapse consecutive duplicate events beyond `retain`.
pub fn transform_log(source: &str, profile: &Profile) -> TransformOutcome {
    let protected = hard_protected(source, profile);
    let protected_bytes: usize = protected.iter().map(|s| s.len()).sum();
    let skip_blank = profile.rules.blank_lines != BlankLineMode::Keep;
    let mut edits = trim_trailing_edits(source, &protected, &[], false, skip_blank);
    edits.extend(blank_line_edits(
        source,
        profile.rules.blank_lines,
        &protected,
        &[],
    ));

    if let Some(retain) = profile.rules.collapse_log_repeats {
        if profile.loss.allow_lossy {
            edits.extend(collapse_log_edits(source, retain, &protected));
        }
    }

    if edits.is_empty() {
        let mut out = TransformOutcome::noop(source);
        out.protected_bytes = protected_bytes;
        return out;
    }
    let records = record_from_edits(&edits);
    let out = apply_edits(source, &edits).text;
    TransformOutcome {
        text: out,
        records,
        warnings: Vec::new(),
        protected_bytes,
    }
}

fn collapse_log_edits(source: &str, retain: usize, protected: &[Span]) -> Vec<Edit> {
    let index = LineIndex::new(source);
    let protected = merge_spans(protected.to_vec());
    let mut edits = Vec::new();
    let mut i = 0usize;
    while i < index.len() {
        let content = match index.content_span(i) {
            Some(c) => c,
            None => {
                i += 1;
                continue;
            }
        };
        if overlaps_sorted(content, &protected) {
            i += 1;
            continue;
        }
        let line = &source[content.start..content.end];
        if line.trim().is_empty() {
            i += 1;
            continue;
        }
        let key = normalize_log_key(line);
        let mut j = i + 1;
        while j < index.len() {
            let cj = match index.content_span(j) {
                Some(c) => c,
                None => break,
            };
            if overlaps_sorted(cj, &protected) {
                break;
            }
            let lj = &source[cj.start..cj.end];
            if lj.trim().is_empty() || normalize_log_key(lj) != key {
                break;
            }
            j += 1;
        }
        let run = j - i;
        if run > retain && retain >= 1 {
            let start = index.full_span(i + retain).unwrap().start;
            let end = index.full_span(j - 1).unwrap().end;
            let collapsed = run - retain;
            let indent: String = line
                .chars()
                .take_while(|c| *c == ' ' || *c == '\t')
                .collect();
            let marker = format!(
                "{}[contextfold: {} repeated log line(s) collapsed]\n",
                indent, collapsed
            );
            edits.push(Edit::replace(
                Span::new(start, end),
                marker,
                RuleId::CollapseLogRepeats,
            ));
        }
        i = j;
    }
    edits
}

fn normalize_log_key(line: &str) -> String {
    let s = line.trim();
    let s = strip_timestamp(s);
    let s = strip_level(s);
    s.trim().to_string()
}

fn strip_timestamp(s: &str) -> &str {
    let b = s.as_bytes();
    if b.len() >= 19
        && b[4] == b'-'
        && b[7] == b'-'
        && (b[10] == b'T' || b[10] == b' ')
        && b[13] == b':'
        && b[16] == b':'
    {
        let mut end = 19;
        if b.get(end) == Some(&b'.') {
            end += 1;
            while end < b.len() && b[end].is_ascii_digit() {
                end += 1;
            }
        }
        if s.as_bytes().get(end) == Some(&b'Z') {
            return s[end + 1..].trim_start();
        }
        if matches!(b.get(end), Some(b'+') | Some(b'-')) {
            end += 1;
            while end < b.len() && (b[end].is_ascii_digit() || b[end] == b':') {
                end += 1;
            }
            return s[end..].trim_start();
        }
        return s[end..].trim_start();
    }
    s
}

fn strip_level(s: &str) -> &str {
    if let Some(rest) = s.strip_prefix('[') {
        if let Some(end) = rest.find(']') {
            let inside = &rest[..end];
            if !inside.is_empty() && inside.chars().all(|c| c.is_ascii_alphabetic()) {
                return rest[end + 1..].trim_start();
            }
        }
    }
    for level in [
        "TRACE", "DEBUG", "INFO", "WARN", "WARNING", "ERROR", "FATAL", "CRITICAL",
    ] {
        if let Some(rest) = s.strip_prefix(level) {
            let boundary = rest.is_empty() || rest.starts_with([':', ' ', ']', '-']);
            if boundary {
                return rest.trim_start_matches([':', ' ', ']', '-']).trim_start();
            }
        }
    }
    s
}

fn record_from_edits(edits: &[Edit]) -> Vec<RuleRecord> {
    build_records(edits, &[])
}
