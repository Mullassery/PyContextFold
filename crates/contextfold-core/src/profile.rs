use crate::error::{EngineError, Result};
use crate::lang::Span;
use serde::{Deserialize, Serialize};

/// How comments are handled.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CommentMode {
    /// Leave comments untouched.
    Keep,
    /// Remove comment nodes entirely.
    Remove,
}

/// How runs of blank lines are handled.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BlankLineMode {
    /// Leave blank-line structure as-is.
    Keep,
    /// Collapse any run of 2+ blank lines to a single blank line.
    CollapseToOne,
    /// Remove all blank lines.
    RemoveAll,
}

/// The set of transformations a profile may apply. Every field defaults to the
/// most conservative behaviour that still makes sense for that rule.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuleSet {
    pub comments: CommentMode,
    /// Strip Python triple-quoted docstrings. This is *documentation* loss and
    /// may change runtime-reachable state such as `__doc__`; it is opt-in.
    pub docstrings: bool,
    pub blank_lines: BlankLineMode,
    pub trim_trailing_whitespace: bool,
    /// Replace declaration bodies with valid placeholders. Explicitly lossy.
    pub interface_only: bool,
    /// Collapse consecutive duplicate log lines beyond `N` retained copies.
    /// Explicitly lossy.
    pub collapse_log_repeats: Option<usize>,
    /// Remove adjacent duplicate non-code Markdown lines. Explicitly lossy.
    pub markdown_dedupe: bool,
}

impl Default for RuleSet {
    fn default() -> Self {
        RuleSet {
            comments: CommentMode::Keep,
            docstrings: false,
            blank_lines: BlankLineMode::Keep,
            trim_trailing_whitespace: false,
            interface_only: false,
            collapse_log_repeats: None,
            markdown_dedupe: false,
        }
    }
}

/// Policy describing content that must never be transformed.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PreservationPolicy {
    /// Never remove import/use statements.
    pub protect_imports: bool,
    /// Never remove error-handling constructs.
    pub protect_error_handling: bool,
    /// Byte ranges the caller marked as protected (e.g. generated headers,
    /// license banners, user-designated regions).
    pub protected_ranges: Vec<Span>,
    /// Any line containing one of these substrings is left byte-for-byte
    /// untouched. Useful for `# contextfold: keep` style markers.
    pub protected_line_markers: Vec<String>,
}

impl Default for PreservationPolicy {
    fn default() -> Self {
        PreservationPolicy {
            protect_imports: true,
            protect_error_handling: true,
            protected_ranges: Vec::new(),
            protected_line_markers: vec![
                "contextfold:keep".to_string(),
                "@contextfold-keep".to_string(),
            ],
        }
    }
}

/// Policy describing what loss the caller permits.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct LossPolicy {
    /// Permit rules that are explicitly labelled lossy (interface-only body
    /// elision, log collapsing, markdown dedupe). Defaults to `false`.
    pub allow_lossy: bool,
}

/// A versioned, documented transformation profile.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Profile {
    pub name: String,
    pub version: u32,
    pub description: String,
    pub rules: RuleSet,
    pub preservation: PreservationPolicy,
    pub loss: LossPolicy,
}

/// Version of every built-in profile. Bump a single profile's version when its
/// behaviour changes; the version is surfaced in every report so callers can
/// detect drift.
pub const PROFILE_SCHEMA_VERSION: u32 = 1;

impl Profile {
    /// All built-in profile names, in stable order.
    pub fn names() -> &'static [&'static str] {
        &[
            "safe",
            "code-review",
            "interface-only",
            "documentation",
            "logs",
            "budgeted",
        ]
    }

    /// Look up a built-in profile by name.
    pub fn named(name: &str) -> Result<Profile> {
        let p = match name {
            "safe" => Profile {
                name: "safe".into(),
                version: PROFILE_SCHEMA_VERSION,
                description:
                    "Conservative: remove comments, collapse blank-line runs, trim trailing \
                     whitespace. Executable statements, imports, conditionals and error handling \
                     are never removed. Docstrings are preserved."
                        .into(),
                rules: RuleSet {
                    comments: CommentMode::Remove,
                    docstrings: false,
                    blank_lines: BlankLineMode::CollapseToOne,
                    trim_trailing_whitespace: true,
                    ..RuleSet::default()
                },
                preservation: PreservationPolicy::default(),
                loss: LossPolicy::default(),
            },
            "code-review" => Profile {
                name: "code-review".into(),
                version: PROFILE_SCHEMA_VERSION,
                description: "Preserve implementation logic and all comments/docstrings. Only \
                     whitespace-level normalisation is applied."
                    .into(),
                rules: RuleSet {
                    comments: CommentMode::Keep,
                    docstrings: false,
                    blank_lines: BlankLineMode::CollapseToOne,
                    trim_trailing_whitespace: true,
                    ..RuleSet::default()
                },
                preservation: PreservationPolicy::default(),
                loss: LossPolicy::default(),
            },
            "interface-only" => Profile {
                name: "interface-only".into(),
                version: PROFILE_SCHEMA_VERSION,
                description:
                    "LOSSY: keep imports, declarations, signatures and docstrings; replace \
                     implementation bodies with valid placeholders. Not behaviour-preserving."
                        .into(),
                rules: RuleSet {
                    comments: CommentMode::Keep,
                    docstrings: false,
                    blank_lines: BlankLineMode::CollapseToOne,
                    trim_trailing_whitespace: true,
                    interface_only: true,
                    ..RuleSet::default()
                },
                preservation: PreservationPolicy::default(),
                loss: LossPolicy { allow_lossy: true },
            },
            "documentation" => Profile {
                name: "documentation".into(),
                version: PROFILE_SCHEMA_VERSION,
                description:
                    "LOSSY: reduce redundant Markdown/prose by collapsing blank lines, trimming \
                     trailing whitespace (preserving hard breaks and code fences) and removing \
                     adjacent duplicate lines. Headings, code blocks, links and lines containing \
                     normative keywords are preserved."
                        .into(),
                rules: RuleSet {
                    comments: CommentMode::Keep,
                    docstrings: false,
                    blank_lines: BlankLineMode::CollapseToOne,
                    trim_trailing_whitespace: true,
                    markdown_dedupe: true,
                    ..RuleSet::default()
                },
                preservation: PreservationPolicy::default(),
                loss: LossPolicy { allow_lossy: true },
            },
            "logs" => Profile {
                name: "logs".into(),
                version: PROFILE_SCHEMA_VERSION,
                description:
                    "LOSSY: collapse consecutive duplicate log events, retaining the configured \
                     number of copies and emitting a marker with the collapsed count. Distinct \
                     events are never merged."
                        .into(),
                rules: RuleSet {
                    comments: CommentMode::Keep,
                    docstrings: false,
                    blank_lines: BlankLineMode::CollapseToOne,
                    trim_trailing_whitespace: true,
                    collapse_log_repeats: Some(1),
                    ..RuleSet::default()
                },
                preservation: PreservationPolicy::default(),
                loss: LossPolicy { allow_lossy: true },
            },
            "budgeted" => Profile {
                name: "budgeted".into(),
                version: PROFILE_SCHEMA_VERSION,
                description:
                    "Apply permitted transformations in a fixed deterministic order to reach a \
                     size/token budget. Escalates to lossy rules only when the caller allows it."
                        .into(),
                rules: RuleSet {
                    comments: CommentMode::Remove,
                    docstrings: true,
                    blank_lines: BlankLineMode::RemoveAll,
                    trim_trailing_whitespace: true,
                    collapse_log_repeats: Some(1),
                    markdown_dedupe: true,
                    ..RuleSet::default()
                },
                preservation: PreservationPolicy::default(),
                loss: LossPolicy { allow_lossy: true },
            },
            other => return Err(EngineError::UnknownProfile(other.to_string())),
        };
        Ok(p)
    }

    /// Build a built-in profile then apply caller overrides.
    pub fn named_with_overrides(name: &str, overrides: ProfileOverrides) -> Result<Profile> {
        let mut profile = Profile::named(name)?;
        if let Some(rules) = overrides.rules {
            if let Some(v) = rules.comments {
                profile.rules.comments = v;
            }
            if let Some(v) = rules.docstrings {
                profile.rules.docstrings = v;
            }
            if let Some(v) = rules.blank_lines {
                profile.rules.blank_lines = v;
            }
            if let Some(v) = rules.trim_trailing_whitespace {
                profile.rules.trim_trailing_whitespace = v;
            }
            if let Some(v) = rules.interface_only {
                profile.rules.interface_only = v;
            }
            if let Some(v) = rules.collapse_log_repeats {
                profile.rules.collapse_log_repeats = Some(v);
            }
            if let Some(v) = rules.markdown_dedupe {
                profile.rules.markdown_dedupe = v;
            }
        }
        if let Some(p) = overrides.preservation {
            if let Some(v) = p.protect_imports {
                profile.preservation.protect_imports = v;
            }
            if let Some(v) = p.protect_error_handling {
                profile.preservation.protect_error_handling = v;
            }
            if let Some(v) = p.protected_ranges {
                profile.preservation.protected_ranges = v;
            }
            if let Some(v) = p.protected_line_markers {
                profile.preservation.protected_line_markers = v;
            }
        }
        if let Some(v) = overrides.allow_lossy {
            profile.loss.allow_lossy = v;
        }
        Ok(profile)
    }
}

/// Optional per-field overrides applied on top of a named profile.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProfileOverrides {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rules: Option<RuleOverrides>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub preservation: Option<PreservationOverrides>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub allow_lossy: Option<bool>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuleOverrides {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub comments: Option<CommentMode>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub docstrings: Option<bool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub blank_lines: Option<BlankLineMode>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub trim_trailing_whitespace: Option<bool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub interface_only: Option<bool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub collapse_log_repeats: Option<usize>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub markdown_dedupe: Option<bool>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct PreservationOverrides {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub protect_imports: Option<bool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub protect_error_handling: Option<bool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub protected_ranges: Option<Vec<Span>>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub protected_line_markers: Option<Vec<String>>,
}
