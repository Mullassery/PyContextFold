use crate::lang::Span;
use crate::rules::RuleId;

/// A single, ordered text replacement: replace `source[span]` with
/// `replacement`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Edit {
    pub span: Span,
    pub replacement: String,
    pub rule: RuleId,
}

impl Edit {
    pub fn remove(span: Span, rule: RuleId) -> Self {
        Edit {
            span,
            replacement: String::new(),
            rule,
        }
    }

    pub fn replace(span: Span, replacement: impl Into<String>, rule: RuleId) -> Self {
        Edit {
            span,
            replacement: replacement.into(),
            rule,
        }
    }
}

/// Maps byte offsets in the original text to offsets in the transformed text.
///
/// Offsets that fell inside a removed/replaced region are clamped to the start
/// of that region in the output.
#[derive(Debug, Clone, Default)]
pub struct OffsetMap {
    /// `(orig_start, orig_end, new_start)` for unchanged segments.
    segs: Vec<(usize, usize, usize)>,
    orig_len: usize,
    new_len: usize,
}

impl OffsetMap {
    fn identity(len: usize) -> Self {
        OffsetMap {
            segs: vec![(0, len, 0)],
            orig_len: len,
            new_len: len,
        }
    }

    pub fn map(&self, orig: usize) -> usize {
        if self.segs.is_empty() {
            return 0;
        }
        let idx = self.segs.partition_point(|(s, _, _)| *s <= orig);
        if idx == 0 {
            return 0;
        }
        let (s, e, ns) = self.segs[idx - 1];
        if orig < e {
            ns + (orig - s)
        } else {
            ns + (e - s)
        }
    }

    pub fn map_span(&self, span: Span) -> Span {
        Span::new(self.map(span.start), self.map(span.end))
    }

    pub fn new_len(&self) -> usize {
        self.new_len
    }

    pub fn orig_len(&self) -> usize {
        self.orig_len
    }
}

/// Result of applying edits.
#[derive(Debug, Clone)]
pub struct ApplyOutcome {
    pub text: String,
    pub applied: usize,
    pub overlaps_dropped: usize,
    pub bytes_removed: i64,
    pub map: OffsetMap,
}

/// Apply a set of edits to `source`.
///
/// Edits are sorted by start offset and applied left-to-right. Overlapping
/// edits are resolved deterministically: the edit with the earlier start wins;
/// a later edit that overlaps an already-committed one is dropped and counted.
pub fn apply_edits(source: &str, edits: &[Edit]) -> ApplyOutcome {
    let mut sorted: Vec<&Edit> = edits.iter().filter(|e| !e.span.is_empty()).collect();
    sorted.sort_by_key(|e| (e.span.start, e.span.end));

    let mut accepted: Vec<&Edit> = Vec::with_capacity(sorted.len());
    let mut last_end = 0usize;
    let mut overlaps_dropped = 0usize;
    for e in sorted {
        if e.span.start < last_end {
            overlaps_dropped += 1;
            continue;
        }
        if e.span.end > source.len()
            || !source.is_char_boundary(e.span.start)
            || !source.is_char_boundary(e.span.end)
        {
            overlaps_dropped += 1;
            continue;
        }
        last_end = e.span.end;
        accepted.push(e);
    }

    let mut out = String::with_capacity(source.len());
    let mut cursor = 0usize;
    let mut new_pos = 0usize;
    let mut bytes_removed = 0i64;
    let mut segs: Vec<(usize, usize, usize)> = Vec::new();
    for e in &accepted {
        out.push_str(&source[cursor..e.span.start]);
        if e.span.start > cursor {
            segs.push((cursor, e.span.start, new_pos));
            new_pos += e.span.start - cursor;
        }
        out.push_str(&e.replacement);
        new_pos += e.replacement.len();
        bytes_removed += e.span.len() as i64 - e.replacement.len() as i64;
        cursor = e.span.end;
    }
    out.push_str(&source[cursor..]);
    if source.len() > cursor {
        segs.push((cursor, source.len(), new_pos));
    }

    let map = if accepted.is_empty() {
        OffsetMap::identity(source.len())
    } else {
        OffsetMap {
            segs,
            orig_len: source.len(),
            new_len: out.len(),
        }
    };

    ApplyOutcome {
        text: out,
        applied: accepted.len(),
        overlaps_dropped,
        bytes_removed,
        map,
    }
}

/// A line-oriented view of a source string, keeping byte spans so edits can be
/// expressed precisely.
pub struct LineIndex<'a> {
    source: &'a str,
    /// `(content span excluding newline, full span including newline)`
    lines: Vec<(Span, Span)>,
}

impl<'a> LineIndex<'a> {
    pub fn new(source: &'a str) -> Self {
        let mut lines = Vec::new();
        let bytes = source.as_bytes();
        let mut start = 0usize;
        let mut i = 0usize;
        while i < bytes.len() {
            if bytes[i] == b'\n' {
                let content_end = if i > start && bytes[i - 1] == b'\r' {
                    i - 1
                } else {
                    i
                };
                lines.push((Span::new(start, content_end), Span::new(start, i + 1)));
                start = i + 1;
            }
            i += 1;
        }
        if start < bytes.len() || lines.is_empty() {
            lines.push((Span::new(start, bytes.len()), Span::new(start, bytes.len())));
        }
        LineIndex { source, lines }
    }

    pub fn len(&self) -> usize {
        self.lines.len()
    }

    pub fn is_empty(&self) -> bool {
        self.lines.is_empty()
    }

    pub fn content_span(&self, i: usize) -> Option<Span> {
        self.lines.get(i).map(|(c, _)| *c)
    }

    pub fn full_span(&self, i: usize) -> Option<Span> {
        self.lines.get(i).map(|(_, f)| *f)
    }

    pub fn content(&self, i: usize) -> Option<&'a str> {
        self.content_span(i).map(|s| &self.source[s.start..s.end])
    }

    pub fn has_trailing_newline(&self, i: usize) -> bool {
        match self.lines.get(i) {
            Some((c, f)) => f.end > c.end,
            None => false,
        }
    }

    pub fn is_blank(&self, i: usize) -> bool {
        self.content(i)
            .map(|l| l.chars().all(|c| c == ' ' || c == '\t'))
            .unwrap_or(false)
    }

    /// Index of the line containing byte `offset`.
    pub fn line_of(&self, offset: usize) -> Option<usize> {
        if self.lines.is_empty() {
            return None;
        }
        let idx = self.lines.partition_point(|(_, f)| f.start <= offset);
        if idx == 0 {
            Some(0)
        } else {
            Some(idx - 1)
        }
    }

    pub fn source(&self) -> &'a str {
        self.source
    }
}

/// Expand a set of byte ranges to whole-line byte ranges, then merge overlaps.
pub fn expand_to_lines(source: &str, spans: &[Span]) -> Vec<Span> {
    let index = LineIndex::new(source);
    let mut out: Vec<Span> = Vec::new();
    for s in spans {
        let mut first: Option<usize> = None;
        let mut last: Option<usize> = None;
        for i in 0..index.len() {
            if let (Some(c), Some(f)) = (index.content_span(i), index.full_span(i)) {
                let touches =
                    f.overlaps(*s) || (s.start == s.end && c.start <= s.start && s.start <= c.end);
                if touches {
                    if first.is_none() {
                        first = Some(i);
                    }
                    last = Some(i);
                }
            }
        }
        if let (Some(fi), Some(li)) = (first, last) {
            let start = index.full_span(fi).unwrap().start;
            let end = index.full_span(li).unwrap().end;
            out.push(Span::new(start, end));
        }
    }
    merge_spans(out)
}

/// Sort and merge overlapping or adjacent spans.
pub fn merge_spans(mut spans: Vec<Span>) -> Vec<Span> {
    spans.retain(|s| !s.is_empty());
    spans.sort_by_key(|s| (s.start, s.end));
    let mut merged: Vec<Span> = Vec::with_capacity(spans.len());
    for s in spans {
        match merged.last_mut() {
            Some(last) if s.start <= last.end => {
                if s.end > last.end {
                    last.end = s.end;
                }
            }
            _ => merged.push(s),
        }
    }
    merged
}

/// True when `span` overlaps any span in `set`.
pub fn overlaps_any(span: Span, set: &[Span]) -> bool {
    set.iter().any(|s| s.overlaps(span))
}

/// Like [`overlaps_any`] but requires `sorted` to be sorted by start and
/// non-overlapping (as produced by [`merge_spans`] or [`SpanIndex`]), so the
/// check runs in `O(log n)` instead of scanning the whole set.
pub fn overlaps_sorted(span: Span, sorted: &[Span]) -> bool {
    if span.is_empty() || sorted.is_empty() {
        return false;
    }
    let idx = sorted.partition_point(|s| s.start < span.end);
    if idx == 0 {
        return false;
    }
    sorted[idx - 1].end > span.start
}
