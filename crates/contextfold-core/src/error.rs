use thiserror::Error;

/// Errors surfaced by the transformation engine.
///
/// The engine is designed to *fail safely*: unsupported formats and parse
/// failures are represented as [`EngineError::UnsupportedFormat`] and are
/// handled by the caller (the CLI and Python bindings fall back to a
/// documented conservative behaviour). They are never silently ignored.
#[derive(Debug, Error)]
pub enum EngineError {
    #[error("unsupported or undetected format: {0}")]
    UnsupportedFormat(String),

    #[error("unknown profile: {0}")]
    UnknownProfile(String),

    #[error("invalid configuration: {0}")]
    InvalidConfig(String),

    #[error("token budget could not be met without exceeding the configured loss policy (limit={limit}, achieved={achieved})")]
    BudgetNotMet { limit: u64, achieved: u64 },

    #[error("internal error: {0}")]
    Internal(String),
}

pub type Result<T> = std::result::Result<T, EngineError>;
