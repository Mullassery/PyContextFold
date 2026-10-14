use serde::{Deserialize, Serialize};

/// A half-open byte range `[start, end)` into a UTF-8 source string.
///
/// All spans produced by analyzers are guaranteed to fall on UTF-8 character
/// boundaries so they can be used to slice the source safely.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct Span {
    pub start: usize,
    pub end: usize,
}

impl Span {
    pub fn new(start: usize, end: usize) -> Self {
        debug_assert!(start <= end, "span start must not exceed end");
        Span { start, end }
    }

    pub fn len(&self) -> usize {
        self.end.saturating_sub(self.start)
    }

    pub fn is_empty(&self) -> bool {
        self.start >= self.end
    }

    /// True when `self` fully contains `other`.
    pub fn contains(&self, other: Span) -> bool {
        self.start <= other.start && other.end <= self.end
    }

    /// True when the two spans share at least one byte and neither is empty.
    pub fn overlaps(&self, other: Span) -> bool {
        self.start < other.end && other.start < self.end
    }
}

/// A content format understood by the engine.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LanguageId {
    Python,
    Rust,
    JavaScript,
    TypeScript,
    Tsx,
    Go,
    Markdown,
    Log,
    Json,
    Text,
    Unknown,
}

impl LanguageId {
    /// Stable machine-readable name, used in reports.
    pub fn as_str(&self) -> &'static str {
        match self {
            LanguageId::Python => "python",
            LanguageId::Rust => "rust",
            LanguageId::JavaScript => "javascript",
            LanguageId::TypeScript => "typescript",
            LanguageId::Tsx => "tsx",
            LanguageId::Go => "go",
            LanguageId::Markdown => "markdown",
            LanguageId::Log => "log",
            LanguageId::Json => "json",
            LanguageId::Text => "text",
            LanguageId::Unknown => "unknown",
        }
    }

    /// True when the language is parsed with a real grammar (Tree-sitter).
    pub fn is_code(&self) -> bool {
        matches!(
            self,
            LanguageId::Python
                | LanguageId::Rust
                | LanguageId::JavaScript
                | LanguageId::TypeScript
                | LanguageId::Tsx
                | LanguageId::Go
        )
    }
}
