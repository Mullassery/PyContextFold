use crate::lang::{LanguageId, Span};
use crate::profile::ProfileOverrides;
use crate::rules::RuleRecord;
use crate::tokenizer::{Budget, BudgetReport};
use serde::{Deserialize, Serialize};

/// How parsing went for the input.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ParseStatus {
    /// Parsed successfully with a real grammar.
    Parsed,
    /// A grammar was available but the input had syntax errors.
    ParseFailed,
    /// No analyzer is registered for the detected format.
    Unsupported,
    /// No grammar applies; a documented conservative fallback was used.
    Fallback,
}

impl ParseStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            ParseStatus::Parsed => "parsed",
            ParseStatus::ParseFailed => "parse_failed",
            ParseStatus::Unsupported => "unsupported",
            ParseStatus::Fallback => "fallback",
        }
    }
}

/// The engine never claims semantic or behavioural equivalence. This enum makes
/// that explicit in the report so downstream tools cannot mistake syntactic
/// validity for semantic preservation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EquivalenceClaim {
    /// Output may differ behaviourally; only structural checks were performed.
    NotGuaranteed,
}

impl EquivalenceClaim {
    pub fn as_str(&self) -> &'static str {
        match self {
            EquivalenceClaim::NotGuaranteed => "not_guaranteed",
        }
    }
}

/// A non-fatal diagnostic.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Warning {
    pub code: String,
    pub message: String,
}

impl Warning {
    pub fn new(code: impl Into<String>, message: impl Into<String>) -> Self {
        Warning {
            code: code.into(),
            message: message.into(),
        }
    }
}

/// Byte/character/line statistics for a text.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct SizeStats {
    pub bytes: usize,
    pub chars: usize,
    pub lines: usize,
}

impl SizeStats {
    pub fn of(text: &str) -> Self {
        SizeStats {
            bytes: text.len(),
            chars: text.chars().count(),
            lines: count_lines(text),
        }
    }
}

fn count_lines(text: &str) -> usize {
    if text.is_empty() {
        return 0;
    }
    let mut n = text.matches('\n').count();
    if !text.ends_with('\n') {
        n += 1;
    }
    n
}

/// A complete transformation report. Serialises to stable JSON for the CLI and
/// for Python callers.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Report {
    pub engine_version: String,
    pub profile: String,
    pub profile_version: u32,
    pub profile_schema_version: u32,
    pub detected_language: String,
    pub parse_status: ParseStatus,
    /// False when any applied rule is lossy, or when lossy output was produced.
    pub behavior_preserving: bool,
    /// Always `"not_guaranteed"`. Present so reports cannot be misread as
    /// semantic-equivalence claims.
    pub semantic_equivalence: String,
    /// Result of re-parsing the output, when a grammar was available.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub syntax_valid: Option<bool>,
    pub input: SizeStats,
    pub output: SizeStats,
    /// `1 - output.bytes / input.bytes`, clamped to `[0, 1]`.
    pub reduction_ratio: f64,
    pub rules: Vec<RuleRecord>,
    pub warnings: Vec<Warning>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub budget: Option<BudgetReport>,
    /// Number of input bytes that fell inside protected ranges.
    pub protected_bytes: usize,
}

/// The full result of a fold operation.
#[derive(Debug, Clone, PartialEq)]
pub struct FoldResult {
    pub output: String,
    pub report: Report,
}

impl FoldResult {
    /// True when the report indicates the transformation was lossy.
    pub fn is_lossy(&self) -> bool {
        !self.report.behavior_preserving
    }
}

/// A fold request: the input plus configuration.
pub struct FoldRequest {
    pub content: String,
    /// Optional path used for format detection only; never read from disk here.
    pub path_hint: Option<String>,
    /// Explicit language override; when `None`, detection is used.
    pub language: Option<LanguageId>,
    pub profile_name: String,
    pub overrides: ProfileOverrides,
    pub budget: Option<Budget>,
}

impl FoldRequest {
    pub fn new(content: impl Into<String>) -> Self {
        FoldRequest {
            content: content.into(),
            path_hint: None,
            language: None,
            profile_name: "safe".to_string(),
            overrides: ProfileOverrides::default(),
            budget: None,
        }
    }

    pub fn with_profile(mut self, name: impl Into<String>) -> Self {
        self.profile_name = name.into();
        self
    }

    pub fn with_path(mut self, path: impl Into<String>) -> Self {
        self.path_hint = Some(path.into());
        self
    }

    pub fn with_language(mut self, language: LanguageId) -> Self {
        self.language = Some(language);
        self
    }

    pub fn with_overrides(mut self, overrides: ProfileOverrides) -> Self {
        self.overrides = overrides;
        self
    }

    pub fn with_protected_ranges(mut self, ranges: Vec<Span>) -> Self {
        self.overrides
            .preservation
            .get_or_insert_with(Default::default)
            .protected_ranges = Some(ranges);
        self
    }

    pub fn with_budget(mut self, budget: Budget) -> Self {
        self.budget = Some(budget);
        self
    }
}
