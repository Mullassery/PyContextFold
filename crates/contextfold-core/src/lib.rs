//! # contextfold-core
//!
//! The PyContextFold transformation core: a local-first, deterministic,
//! structure-aware engine that reduces source code, documentation, logs and
//! structured text into compact representations for LLM consumption.
//!
//! ## Scope
//!
//! The core owns content-aware parsing (via caller-registered analyzers),
//! structural transformations, redundancy reduction, configurable preservation
//! policies, budget-constrained folding, output validation and transformation
//! reports. It does **not** count provider tokens (see the [`tokenizer`]
//! interface), discover/retrieve context, run inference, process PDFs or manage
//! agents.
//!
//! ## Guarantees
//!
//! * Deterministic: same `(input, profile, engine version, registry)` produces
//!   byte-identical output.
//! * Conservative by default: the `safe` profile never removes executable
//!   statements, imports, conditions or error handling.
//! * Explicit about loss: lossy rules are labelled in the report; the engine
//!   never claims semantic equivalence, only (optionally) syntactic validity.
//! * No network access and no logging of source content.

pub mod analyzer;
pub mod edit;
pub mod engine;
pub mod error;
pub mod lang;
pub mod model;
pub mod profile;
pub mod rules;
pub mod tokenizer;
pub mod transform;

pub use analyzer::{
    detect_language, language_from_extension, Analysis, Declaration, DeclarationKind,
    LanguageAnalyzer, Registry,
};
pub use edit::{apply_edits, Edit, LineIndex};
pub use engine::{Engine, ENGINE_VERSION};
pub use error::{EngineError, Result};
pub use lang::{LanguageId, Span};
pub use model::{
    EquivalenceClaim, FoldRequest, FoldResult, ParseStatus, Report, SizeStats, Warning,
};
pub use profile::{
    BlankLineMode, CommentMode, LossPolicy, PreservationPolicy, Profile, ProfileOverrides,
    RuleOverrides, RuleSet, PROFILE_SCHEMA_VERSION,
};
pub use rules::{RuleId, RuleRecord};
pub use tokenizer::{Budget, BudgetMetric, BudgetReport, Tokenizer};
