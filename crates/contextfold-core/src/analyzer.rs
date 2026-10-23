use crate::lang::{LanguageId, Span};
use serde::{Deserialize, Serialize};

/// The kind of a top-level-ish declaration relevant to interface-only output.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DeclarationKind {
    Function,
    Method,
    Class,
    Struct,
    Enum,
    Trait,
    Interface,
    TypeAlias,
    Const,
    Static,
    Module,
    Other,
}

/// A declaration discovered in the syntax tree.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Declaration {
    pub kind: DeclarationKind,
    pub name: String,
    /// Full span of the declaration (signature + body where applicable).
    pub span: Span,
    /// Byte offset at which the declaration's *signature/header* ends and its
    /// body begins. Equal to `span.end` for bodyless declarations.
    pub body_start: usize,
    /// Byte offset of the end of the body, or `span.end` if bodyless.
    pub body_end: usize,
    /// True when the declaration actually has a replaceable body.
    pub has_body: bool,
}

/// Structural facts extracted from a parsed source, consumed by the
/// transformation pipeline. All spans are byte ranges into the original UTF-8
/// source.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Analysis {
    pub language: LanguageId,
    /// True when the source parsed without syntax errors.
    pub parsed: bool,
    /// Comment nodes (line + block). Removal candidates.
    pub comment_spans: Vec<Span>,
    /// Triple-quoted / doc-comment strings that act as documentation.
    pub docstring_spans: Vec<Span>,
    /// All string-literal spans. Used to keep whitespace passes out of them.
    pub string_spans: Vec<Span>,
    /// Import / use / require statements. Protected by policy.
    pub import_spans: Vec<Span>,
    /// Error-handling constructs (`try`/`except`, `catch`, `?`/`Result` guards
    /// where detectable). Protected by policy.
    pub error_handling_spans: Vec<Span>,
    /// Declarations for interface-only projection.
    pub declarations: Vec<Declaration>,
}

impl Analysis {
    pub fn empty(language: LanguageId) -> Self {
        Analysis {
            language,
            parsed: false,
            comment_spans: Vec::new(),
            docstring_spans: Vec::new(),
            string_spans: Vec::new(),
            import_spans: Vec::new(),
            error_handling_spans: Vec::new(),
            declarations: Vec::new(),
        }
    }
}

/// A parse-and-analyze backend for one or more [`LanguageId`]s.
///
/// Implementations live in `contextfold-parsers` (Tree-sitter) and in the
/// built-in format analyzers. Core never depends on a specific parser.
pub trait LanguageAnalyzer: Send + Sync {
    /// The primary language this analyzer handles.
    fn language(&self) -> LanguageId;

    /// File extensions (lowercase, without dot) this analyzer claims.
    fn extensions(&self) -> &'static [&'static str];

    /// Parse `source` and extract structural facts. Implementations must
    /// return `Analysis::empty` (with `parsed = false`) on parse failure rather
    /// than panicking.
    fn analyze(&self, source: &str) -> Analysis;

    /// Validate that `source` is syntactically valid for this language.
    ///
    /// This is a *syntactic* check only. It says nothing about semantic or
    /// behavioural equivalence.
    fn validate(&self, source: &str) -> bool {
        self.analyze(source).parsed
    }
}

/// A registry of analyzers keyed by [`LanguageId`].
#[derive(Default)]
pub struct Registry {
    analyzers: Vec<Box<dyn LanguageAnalyzer>>,
}

impl Registry {
    pub fn new() -> Self {
        Registry {
            analyzers: Vec::new(),
        }
    }

    pub fn register<A: LanguageAnalyzer + 'static>(mut self, analyzer: A) -> Self {
        self.analyzers.push(Box::new(analyzer));
        self
    }

    pub fn get(&self, language: LanguageId) -> Option<&dyn LanguageAnalyzer> {
        self.analyzers
            .iter()
            .find(|a| a.language() == language)
            .map(|a| a.as_ref())
    }

    pub fn languages(&self) -> Vec<LanguageId> {
        self.analyzers.iter().map(|a| a.language()).collect()
    }

    /// Detect a language from a path hint and/or content, then return the
    /// matching analyzer.
    pub fn detect_and_get(
        &self,
        path_hint: Option<&str>,
        content: &str,
    ) -> (LanguageId, Option<&dyn LanguageAnalyzer>) {
        let language = detect_language(path_hint, content);
        let analyzer = self.get(language);
        (language, analyzer)
    }
}

/// Heuristic format detection.
///
/// Detection is deliberately conservative: an accurate extension wins, then a
/// small set of content heuristics, otherwise [`LanguageId::Unknown`]. It never
/// guesses a code language so aggressively that it would mis-transform content.
pub fn detect_language(path_hint: Option<&str>, content: &str) -> LanguageId {
    if let Some(path) = path_hint {
        if let Some(lang) = language_from_extension(path) {
            return lang;
        }
        if let Some(name) = path.rsplit(['/', '\\']).next() {
            match name.to_ascii_lowercase().as_str() {
                "makefile" | "dockerfile" => return LanguageId::Text,
                _ => {}
            }
        }
    }
    language_from_content(content)
}

/// Map a file extension to a language. Exposed so analyzer registries and
/// callers can share one source of truth.
pub fn language_from_extension(path: &str) -> Option<LanguageId> {
    let ext = path.rsplit('.').next()?.to_ascii_lowercase();
    let lang = match ext.as_str() {
        "py" | "pyi" | "pyw" => LanguageId::Python,
        "rs" => LanguageId::Rust,
        "js" | "mjs" | "cjs" | "jsx" => LanguageId::JavaScript,
        "ts" | "mts" | "cts" => LanguageId::TypeScript,
        "tsx" => LanguageId::Tsx,
        "go" => LanguageId::Go,
        "md" | "markdown" | "mdx" => LanguageId::Markdown,
        "json" => LanguageId::Json,
        "log" => LanguageId::Log,
        "txt" | "text" | "rst" => LanguageId::Text,
        _ => return None,
    };
    Some(lang)
}

/// Content-based heuristics, used only when there is no usable path hint.
fn language_from_content(content: &str) -> LanguageId {
    let sample: &str = {
        let mut end = content.len().min(4096);
        while end > 0 && !content.is_char_boundary(end) {
            end -= 1;
        }
        &content[..end]
    };
    let trimmed = sample.trim_start();

    if trimmed.starts_with("<?xml") || trimmed.starts_with("<!DOCTYPE") {
        return LanguageId::Unknown;
    }
    if (trimmed.starts_with('{') || trimmed.starts_with('['))
        && serde_json::from_str::<serde_json::Value>(sample).is_ok()
    {
        return LanguageId::Json;
    }
    if looks_like_log(sample) {
        return LanguageId::Log;
    }
    if looks_like_markdown(sample) {
        return LanguageId::Markdown;
    }
    LanguageId::Unknown
}

fn looks_like_markdown(sample: &str) -> bool {
    let mut heading = false;
    let mut list = false;
    for line in sample.lines().take(40) {
        let t = line.trim_start();
        if t.starts_with('#') && matches!(t.chars().nth(1), None | Some(' ' | '#')) {
            heading = true;
        } else if t.starts_with("- ") || t.starts_with("* ") || t.starts_with("```") {
            list = true;
        }
    }
    heading && list
}

fn looks_like_log(sample: &str) -> bool {
    let mut matches = 0usize;
    let mut lines = 0usize;
    for line in sample.lines().take(20) {
        if line.trim().is_empty() {
            continue;
        }
        lines += 1;
        if line_looks_like_log(line) {
            matches += 1;
        }
    }
    lines > 0 && matches * 2 >= lines
}

/// True when a line begins with a common log prefix: ISO timestamp, syslog
/// timestamp, bracketed level, or `LEVEL:` marker.
fn line_looks_like_log(line: &str) -> bool {
    let t = line.trim_start();
    // 2024-01-02T03:04:05 or 2024-01-02 03:04:05
    let b = t.as_bytes();
    if b.len() >= 19 && b[4] == b'-' && b[7] == b'-' && (b[10] == b'T' || b[10] == b' ') {
        return true;
    }
    // [INFO] / [ERROR]
    if t.starts_with('[') {
        if let Some(end) = t.find(']') {
            let inside = &t[1..end];
            if inside.chars().all(|c| c.is_ascii_alphabetic()) && !inside.is_empty() {
                return true;
            }
        }
    }
    // INFO: / ERROR / WARN
    for level in [
        "TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL", "CRITICAL",
    ] {
        if let Some(rest) = t.strip_prefix(level) {
            if rest.is_empty() || rest.starts_with([':', ' ', ']']) {
                return true;
            }
        }
    }
    false
}
