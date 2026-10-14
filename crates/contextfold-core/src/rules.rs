use serde::{Deserialize, Serialize};

/// Stable identifiers for every transformation rule the engine can apply.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RuleId {
    StripComments,
    StripDocstrings,
    CollapseBlankLines,
    TrimTrailingWhitespace,
    InterfaceOnly,
    CollapseLogRepeats,
    MarkdownDedupe,
}

impl RuleId {
    pub fn as_str(&self) -> &'static str {
        match self {
            RuleId::StripComments => "strip_comments",
            RuleId::StripDocstrings => "strip_docstrings",
            RuleId::CollapseBlankLines => "collapse_blank_lines",
            RuleId::TrimTrailingWhitespace => "trim_trailing_whitespace",
            RuleId::InterfaceOnly => "interface_only",
            RuleId::CollapseLogRepeats => "collapse_log_repeats",
            RuleId::MarkdownDedupe => "markdown_dedupe",
        }
    }

    /// Whether applying this rule can discard information that is not
    /// reproducible from the output (beyond formatting).
    pub fn is_lossy(&self) -> bool {
        matches!(
            self,
            RuleId::StripDocstrings
                | RuleId::InterfaceOnly
                | RuleId::CollapseLogRepeats
                | RuleId::MarkdownDedupe
        )
    }

    pub fn description(&self) -> &'static str {
        match self {
            RuleId::StripComments => "Removed comment nodes.",
            RuleId::StripDocstrings => "Removed Python docstrings.",
            RuleId::CollapseBlankLines => "Collapsed runs of blank lines.",
            RuleId::TrimTrailingWhitespace => "Trimmed trailing whitespace on trivia lines.",
            RuleId::InterfaceOnly => "Replaced declaration bodies with placeholders (lossy).",
            RuleId::CollapseLogRepeats => "Collapsed consecutive duplicate log events (lossy).",
            RuleId::MarkdownDedupe => "Removed adjacent duplicate prose lines (lossy).",
        }
    }
}

/// A record of one rule's effect, included in the report.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuleRecord {
    pub rule: RuleId,
    pub rule_name: String,
    /// Number of individual changes (edits or collapsed regions) applied.
    pub changes: usize,
    /// Bytes removed by this rule (net).
    pub bytes_removed: i64,
    /// Whether this rule is intrinsically lossy.
    pub lossy: bool,
    pub description: String,
}

impl RuleRecord {
    pub fn new(rule: RuleId, changes: usize, bytes_removed: i64) -> Self {
        RuleRecord {
            rule,
            rule_name: rule.as_str().to_string(),
            changes,
            bytes_removed,
            lossy: rule.is_lossy(),
            description: rule.description().to_string(),
        }
    }
}
