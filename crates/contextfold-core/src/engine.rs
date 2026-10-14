use crate::analyzer::{detect_language, Registry};
use crate::error::{EngineError, Result};
use crate::lang::LanguageId;
use crate::model::{
    EquivalenceClaim, FoldRequest, FoldResult, ParseStatus, Report, SizeStats, Warning,
};
use crate::profile::Profile;
use crate::rules::RuleRecord;
use crate::tokenizer::BudgetReport;
use crate::transform::{
    transform_code, transform_json, transform_log, transform_markdown, transform_text,
    TransformOutcome,
};

/// The engine version, surfaced in every report.
pub const ENGINE_VERSION: &str = env!("CARGO_PKG_VERSION");

/// The transformation engine.
///
/// The engine is stateless with respect to input content: it never reads from or
/// writes to disk. Callers provide content; the engine returns transformed
/// content plus a report. It is deterministic for a given
/// `(input, profile, engine version, registry)` tuple.
pub struct Engine {
    registry: Registry,
}

impl Engine {
    pub fn new(registry: Registry) -> Self {
        Engine { registry }
    }

    pub fn registry(&self) -> &Registry {
        &self.registry
    }

    /// Transform a single piece of content.
    pub fn fold(&self, request: FoldRequest) -> Result<FoldResult> {
        let profile = Profile::named_with_overrides(&request.profile_name, request.overrides)?;
        let content = &request.content;
        let input = SizeStats::of(content);

        let language = request
            .language
            .unwrap_or_else(|| detect_language(request.path_hint.as_deref(), content));

        let mut warnings: Vec<Warning> = Vec::new();
        let parse_status;
        let mut syntax_valid: Option<bool> = None;

        let outcome: TransformOutcome = if language.is_code() {
            match self.registry.get(language) {
                Some(analyzer) => {
                    let analysis = analyzer.analyze(content);
                    parse_status = if analysis.parsed {
                        ParseStatus::Parsed
                    } else {
                        ParseStatus::ParseFailed
                    };
                    let out = transform_code(content, &analysis, analyzer, &profile);
                    syntax_valid = Some(if out.text == *content {
                        analysis.parsed
                    } else {
                        analyzer.validate(&out.text)
                    });
                    out
                }
                None => {
                    parse_status = ParseStatus::Unsupported;
                    warnings.push(Warning::new(
                        "unsupported_language",
                        format!(
                            "no analyzer registered for {}; content left unchanged",
                            language.as_str()
                        ),
                    ));
                    noop(content)
                }
            }
        } else {
            match language {
                LanguageId::Markdown => {
                    parse_status = ParseStatus::Parsed;
                    transform_markdown(content, &profile)
                }
                LanguageId::Log => {
                    parse_status = ParseStatus::Parsed;
                    transform_log(content, &profile)
                }
                LanguageId::Json => {
                    let out = transform_json(content, &profile);
                    let valid = serde_json::from_str::<serde_json::Value>(content).is_ok();
                    parse_status = if valid {
                        ParseStatus::Parsed
                    } else {
                        ParseStatus::Fallback
                    };
                    syntax_valid = Some(valid);
                    out
                }
                LanguageId::Text => {
                    parse_status = ParseStatus::Fallback;
                    transform_text(content, &profile)
                }
                _ => {
                    parse_status = ParseStatus::Unsupported;
                    warnings.push(Warning::new(
                        "unsupported_format",
                        "format could not be detected; content left unchanged",
                    ));
                    noop(content)
                }
            }
        };

        warnings.extend(outcome.warnings.iter().cloned());

        let output = SizeStats::of(&outcome.text);
        let behavior_preserving = outcome.records.iter().all(|r| !(r.lossy && r.changes > 0));

        let reduction_ratio = if input.bytes == 0 {
            0.0
        } else {
            let r = 1.0 - (output.bytes as f64 / input.bytes as f64);
            r.clamp(0.0, 1.0)
        };

        let budget_report = match &request.budget {
            Some(budget) => {
                let limit = budget.max;
                let in_measure = budget.measure(content)?;
                let out_measure = budget.measure(&outcome.text)?;
                let met = out_measure <= limit;
                if !met {
                    warnings.push(Warning::new(
                        "budget_not_met",
                        format!(
                            "output size {} exceeds budget limit {} under metric '{}'",
                            out_measure,
                            limit,
                            metric_name(budget)
                        ),
                    ));
                }
                Some(BudgetReport {
                    metric: metric_name(budget).to_string(),
                    tokenizer: budget.tokenizer.as_ref().map(|t| t.name().to_string()),
                    exact_tokens: matches!(budget.metric, crate::tokenizer::BudgetMetric::Tokens),
                    limit,
                    input: in_measure,
                    output: out_measure,
                    met,
                })
            }
            None => None,
        };

        let report = Report {
            engine_version: ENGINE_VERSION.to_string(),
            profile: profile.name.clone(),
            profile_version: profile.version,
            profile_schema_version: crate::profile::PROFILE_SCHEMA_VERSION,
            detected_language: language.as_str().to_string(),
            parse_status,
            behavior_preserving,
            semantic_equivalence: EquivalenceClaim::NotGuaranteed.as_str().to_string(),
            syntax_valid,
            input,
            output,
            reduction_ratio,
            rules: dedupe_records(outcome.records),
            warnings,
            budget: budget_report,
            protected_bytes: outcome.protected_bytes,
        };

        Ok(FoldResult {
            output: outcome.text,
            report,
        })
    }

    /// Convenience: fold with the `safe` profile using built-in detection.
    pub fn fold_safe(&self, content: &str, path_hint: Option<&str>) -> Result<FoldResult> {
        let mut req = FoldRequest::new(content);
        if let Some(p) = path_hint {
            req.path_hint = Some(p.to_string());
        }
        self.fold(req)
    }
}

fn noop(content: &str) -> TransformOutcome {
    TransformOutcome {
        text: content.to_string(),
        records: Vec::new(),
        warnings: Vec::new(),
        protected_bytes: 0,
    }
}

fn metric_name(budget: &crate::tokenizer::Budget) -> &'static str {
    use crate::tokenizer::BudgetMetric;
    match budget.metric {
        BudgetMetric::Tokens => "tokens",
        BudgetMetric::Bytes => "bytes",
        BudgetMetric::Characters => "characters",
    }
}

/// Merge duplicate rule records (e.g. whitespace rules emitted from both the
/// structural and whitespace passes) into one entry per rule.
fn dedupe_records(records: Vec<RuleRecord>) -> Vec<RuleRecord> {
    let mut merged: Vec<RuleRecord> = Vec::new();
    for r in records {
        if let Some(existing) = merged.iter_mut().find(|e| e.rule == r.rule) {
            existing.changes += r.changes;
            existing.bytes_removed += r.bytes_removed;
        } else {
            merged.push(r);
        }
    }
    merged
}

impl Engine {
    /// Build an engine with no analyzers. A caller that only transforms
    /// Markdown/Log/Text/JSON can use this.
    pub fn bare() -> Self {
        Engine::new(Registry::new())
    }
}

impl Default for Engine {
    fn default() -> Self {
        Engine::bare()
    }
}

/// Guard against callers passing a code language to an engine without the
/// matching analyzer.
impl Engine {
    pub fn has_language(&self, language: LanguageId) -> bool {
        self.registry.get(language).is_some()
    }
}

// Re-export for ergonomic use in callers that build requests.
pub use crate::error::EngineError as FoldError;

/// Marker to keep the `FoldError` re-export used even without external use.
#[allow(dead_code)]
fn _fold_error_is_send_sync() {
    fn assert<T: Send + Sync + std::error::Error>() {}
    assert::<EngineError>();
}
