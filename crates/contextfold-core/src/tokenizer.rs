use crate::error::{EngineError, Result};
use serde::{Deserialize, Serialize};

/// A caller-supplied token counter.
///
/// PyContextFold deliberately does **not** ship a provider tokenizer catalogue;
/// that is PyTokenCalc's responsibility. Callers may supply any counter through
/// this interface. When no counter is supplied, budgets are evaluated with a
/// byte/character metric that is *never* reported as a token count.
pub trait Tokenizer: Send + Sync {
    /// Human-readable name, e.g. `"pycalc:openai:gpt-4o"`.
    fn name(&self) -> &str;
    /// Exact token count for `text` as defined by this tokenizer.
    fn count(&self, text: &str) -> u64;
}

/// The metric used to evaluate a budget.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BudgetMetric {
    /// Exact token count from a caller-supplied [`Tokenizer`].
    Tokens,
    /// UTF-8 byte count (an approximation; not a token count).
    Bytes,
    /// Unicode scalar-value count (an approximation; not a token count).
    Characters,
}

/// A size/token budget request.
pub struct Budget {
    pub max: u64,
    pub metric: BudgetMetric,
    pub tokenizer: Option<Box<dyn Tokenizer>>,
}

impl Budget {
    pub fn bytes(max: u64) -> Self {
        Budget {
            max,
            metric: BudgetMetric::Bytes,
            tokenizer: None,
        }
    }

    pub fn characters(max: u64) -> Self {
        Budget {
            max,
            metric: BudgetMetric::Characters,
            tokenizer: None,
        }
    }

    pub fn tokens<T: Tokenizer + 'static>(max: u64, tokenizer: T) -> Self {
        Budget {
            max,
            metric: BudgetMetric::Tokens,
            tokenizer: Some(Box::new(tokenizer)),
        }
    }

    /// Measure `text` under this budget's metric.
    pub fn measure(&self, text: &str) -> Result<u64> {
        match self.metric {
            BudgetMetric::Bytes => Ok(text.len() as u64),
            BudgetMetric::Characters => Ok(text.chars().count() as u64),
            BudgetMetric::Tokens => {
                let tok = self.tokenizer.as_ref().ok_or_else(|| {
                    EngineError::InvalidConfig("token budget requires a tokenizer".to_string())
                })?;
                Ok(tok.count(text))
            }
        }
    }
}

/// Outcome of a budget evaluation, included in the report.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BudgetReport {
    /// Metric name: `"tokens"`, `"bytes"` or `"characters"`.
    pub metric: String,
    /// Tokenizer name when the metric is exact tokens.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tokenizer: Option<String>,
    /// True when `metric` is an exact token count.
    pub exact_tokens: bool,
    pub limit: u64,
    pub input: u64,
    pub output: u64,
    pub met: bool,
}
