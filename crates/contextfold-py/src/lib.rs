//! PyO3 native bindings for PyContextFold.
//!
//! This module is intentionally thin: all parsing, transformation, validation
//! and reporting logic lives in `contextfold-core` and `contextfold-parsers`.
//! Python is an ergonomic interface only.

use pyo3::exceptions::{PyIOError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyList, PyString};

use contextfold_core::analyzer::language_from_extension;
use contextfold_core::model::{FoldRequest, FoldResult as CoreFoldResult};
use contextfold_core::profile::{PreservationOverrides, Profile, ProfileOverrides};
use contextfold_core::tokenizer::{Budget, BudgetMetric, Tokenizer};
use contextfold_core::{Engine, LanguageId, Span};
use contextfold_parsers::standard_registry;

pyo3::create_exception!(_core, ContextFoldError, pyo3::exceptions::PyException);
pyo3::create_exception!(_core, UnknownProfileError, ContextFoldError);
pyo3::create_exception!(_core, InvalidConfigError, ContextFoldError);
pyo3::create_exception!(_core, BudgetNotMetError, ContextFoldError);

fn map_engine_error(err: contextfold_core::EngineError) -> PyErr {
    use contextfold_core::EngineError::*;
    match err {
        UnknownProfile(m) => UnknownProfileError::new_err(m),
        InvalidConfig(m) => InvalidConfigError::new_err(m),
        BudgetNotMet { limit, achieved } => BudgetNotMetError::new_err(format!(
            "budget not met: limit={limit}, achieved={achieved}"
        )),
        UnsupportedFormat(m) => ContextFoldError::new_err(m),
        Internal(m) => ContextFoldError::new_err(m),
    }
}

/// Convert a `serde_json::Value` into a native Python object.
fn json_to_py(py: Python<'_>, v: &serde_json::Value) -> PyObject {
    use serde_json::Value::*;
    match v {
        Null => py.None(),
        Bool(b) => PyBool::new(py, *b).to_owned().into_any().unbind(),
        Number(n) => {
            if let Some(i) = n.as_i64() {
                i.into_pyobject(py)
                    .map(|o| o.into_any().unbind())
                    .unwrap_or_else(|_| py.None())
            } else if let Some(f) = n.as_f64() {
                f.into_pyobject(py)
                    .map(|o| o.into_any().unbind())
                    .unwrap_or_else(|_| py.None())
            } else {
                py.None()
            }
        }
        String(s) => PyString::new(py, s).into_any().unbind(),
        Array(a) => {
            let list = PyList::empty(py);
            for item in a {
                let _ = list.append(json_to_py(py, item));
            }
            list.into_any().unbind()
        }
        Object(o) => {
            let dict = PyDict::new(py);
            for (k, val) in o {
                let _ = dict.set_item(k, json_to_py(py, val));
            }
            dict.into_any().unbind()
        }
    }
}

/// A caller-supplied Python tokenizer implementing `count(text) -> int`.
struct PyTokenizer {
    obj: Py<PyAny>,
    name: String,
}

impl Tokenizer for PyTokenizer {
    fn name(&self) -> &str {
        &self.name
    }
    fn count(&self, text: &str) -> u64 {
        Python::with_gil(|py| {
            self.obj
                .call_method1(py, "count", (text,))
                .and_then(|r| r.extract::<u64>(py))
                .unwrap_or(u64::MAX)
        })
    }
}

fn build_overrides(
    allow_lossy: Option<bool>,
    protected_ranges: Option<Vec<(usize, usize)>>,
    protected_line_markers: Option<Vec<String>>,
) -> ProfileOverrides {
    let mut ov = ProfileOverrides::default();
    if let Some(v) = allow_lossy {
        ov.allow_lossy = Some(v);
    }
    if protected_ranges.is_some() || protected_line_markers.is_some() {
        let mut p = PreservationOverrides::default();
        if let Some(r) = protected_ranges {
            p.protected_ranges = Some(r.into_iter().map(|(s, e)| Span::new(s, e)).collect());
        }
        if let Some(m) = protected_line_markers {
            p.protected_line_markers = Some(m);
        }
        ov.preservation = Some(p);
    }
    ov
}

fn parse_language(name: &str) -> PyResult<LanguageId> {
    use LanguageId::*;
    Ok(match name.to_ascii_lowercase().as_str() {
        "python" | "py" => Python,
        "rust" | "rs" => Rust,
        "javascript" | "js" => JavaScript,
        "typescript" | "ts" => TypeScript,
        "tsx" => Tsx,
        "go" | "golang" => Go,
        "markdown" | "md" => Markdown,
        "log" | "logs" => Log,
        "json" => Json,
        "text" | "txt" => Text,
        "unknown" => Unknown,
        other => {
            // Try extension detection as a fallback (e.g. "foo.py").
            match language_from_extension(other) {
                Some(l) => l,
                None => return Err(PyValueError::new_err(format!("unknown language: {other}"))),
            }
        }
    })
}

/// A typed transformation result.
#[pyclass(name = "FoldResult")]
#[derive(Clone)]
pub struct PyFoldResult {
    #[pyo3(get)]
    output: String,
    report: contextfold_core::Report,
}

#[pymethods]
impl PyFoldResult {
    #[getter]
    fn report(&self) -> PyReport {
        PyReport {
            inner: self.report.clone(),
        }
    }

    /// True when the transformation was lossy.
    #[getter]
    fn lossy(&self) -> bool {
        !self.report.behavior_preserving
    }

    fn __repr__(&self) -> String {
        format!(
            "FoldResult(output_bytes={}, reduction={:.3}, lossy={})",
            self.report.output.bytes, self.report.reduction_ratio, !self.report.behavior_preserving
        )
    }
}

/// A transformation report.
#[pyclass(name = "Report")]
#[derive(Clone)]
pub struct PyReport {
    inner: contextfold_core::Report,
}

#[pymethods]
impl PyReport {
    #[getter]
    fn engine_version(&self) -> String {
        self.inner.engine_version.clone()
    }
    #[getter]
    fn profile(&self) -> String {
        self.inner.profile.clone()
    }
    #[getter]
    fn profile_version(&self) -> u32 {
        self.inner.profile_version
    }
    #[getter]
    fn detected_language(&self) -> String {
        self.inner.detected_language.clone()
    }
    #[getter]
    fn parse_status(&self) -> String {
        self.inner.parse_status.as_str().to_string()
    }
    #[getter]
    fn behavior_preserving(&self) -> bool {
        self.inner.behavior_preserving
    }
    #[getter]
    fn semantic_equivalence(&self) -> String {
        self.inner.semantic_equivalence.clone()
    }
    #[getter]
    fn syntax_valid(&self) -> Option<bool> {
        self.inner.syntax_valid
    }
    #[getter]
    fn reduction_ratio(&self) -> f64 {
        self.inner.reduction_ratio
    }
    #[getter]
    fn input_bytes(&self) -> usize {
        self.inner.input.bytes
    }
    #[getter]
    fn output_bytes(&self) -> usize {
        self.inner.output.bytes
    }
    #[getter]
    fn input_chars(&self) -> usize {
        self.inner.input.chars
    }
    #[getter]
    fn output_chars(&self) -> usize {
        self.inner.output.chars
    }
    #[getter]
    fn input_lines(&self) -> usize {
        self.inner.input.lines
    }
    #[getter]
    fn output_lines(&self) -> usize {
        self.inner.output.lines
    }
    #[getter]
    fn protected_bytes(&self) -> usize {
        self.inner.protected_bytes
    }

    /// The full report as a Python dict.
    fn to_dict(&self, py: Python<'_>) -> PyResult<PyObject> {
        let value = serde_json::to_value(&self.inner)
            .map_err(|e| ContextFoldError::new_err(format!("failed to serialize report: {e}")))?;
        Ok(json_to_py(py, &value))
    }

    /// Stable JSON string of the full report.
    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(&self.inner)
            .map_err(|e| ContextFoldError::new_err(format!("failed to serialize report: {e}")))
    }

    fn __repr__(&self) -> String {
        format!(
            "Report(profile={:?}, language={:?}, parse_status={}, reduction={:.3})",
            self.inner.profile,
            self.inner.detected_language,
            self.inner.parse_status.as_str(),
            self.inner.reduction_ratio
        )
    }
}

/// A typed configuration object describing a transformation request.
#[pyclass(name = "FoldRequest")]
pub struct PyFoldRequest {
    #[pyo3(get, set)]
    content: String,
    #[pyo3(get, set)]
    profile: String,
    #[pyo3(get, set)]
    path: Option<String>,
    #[pyo3(get, set)]
    language: Option<String>,
    #[pyo3(get, set)]
    allow_lossy: Option<bool>,
    #[pyo3(get, set)]
    budget_bytes: Option<u64>,
    #[pyo3(get, set)]
    budget_chars: Option<u64>,
    #[pyo3(get, set)]
    budget_tokens: Option<u64>,
    #[pyo3(get, set)]
    protected_ranges: Option<Vec<(usize, usize)>>,
    #[pyo3(get, set)]
    protected_line_markers: Option<Vec<String>>,
    tokenizer: Option<Py<PyAny>>,
}

#[pymethods]
impl PyFoldRequest {
    #[new]
    #[pyo3(signature = (
        content,
        profile = "safe".to_string(),
        path = None,
        language = None,
        allow_lossy = None,
        budget_bytes = None,
        budget_chars = None,
        budget_tokens = None,
        tokenizer = None,
        protected_ranges = None,
        protected_line_markers = None,
    ))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        content: String,
        profile: String,
        path: Option<String>,
        language: Option<String>,
        allow_lossy: Option<bool>,
        budget_bytes: Option<u64>,
        budget_chars: Option<u64>,
        budget_tokens: Option<u64>,
        tokenizer: Option<Py<PyAny>>,
        protected_ranges: Option<Vec<(usize, usize)>>,
        protected_line_markers: Option<Vec<String>>,
    ) -> Self {
        PyFoldRequest {
            content,
            profile,
            path,
            language,
            allow_lossy,
            budget_bytes,
            budget_chars,
            budget_tokens,
            protected_ranges,
            protected_line_markers,
            tokenizer,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "FoldRequest(profile={:?}, language={:?}, path={:?})",
            self.profile, self.language, self.path
        )
    }
}

impl PyFoldRequest {
    fn to_core(&self) -> PyResult<FoldRequest> {
        let mut req = FoldRequest::new(self.content.clone());
        req.profile_name = self.profile.clone();
        req.path_hint = self.path.clone();
        req.overrides = build_overrides(
            self.allow_lossy,
            self.protected_ranges.clone(),
            self.protected_line_markers.clone(),
        );
        if let Some(lang) = &self.language {
            req.language = Some(parse_language(lang)?);
        }
        let budget_choices = [
            self.budget_bytes.is_some(),
            self.budget_chars.is_some(),
            self.budget_tokens.is_some(),
        ]
        .into_iter()
        .filter(|b| *b)
        .count();
        if budget_choices > 1 {
            return Err(InvalidConfigError::new_err(
                "specify at most one of budget_bytes, budget_chars, budget_tokens",
            ));
        }
        if let Some(b) = self.budget_bytes {
            req.budget = Some(Budget::bytes(b));
        } else if let Some(b) = self.budget_chars {
            req.budget = Some(Budget::characters(b));
        } else if let Some(b) = self.budget_tokens {
            let tokenizer = self.tokenizer.as_ref().ok_or_else(|| {
                InvalidConfigError::new_err("budget_tokens requires a tokenizer object")
            })?;
            let name: String = Python::with_gil(|py| {
                tokenizer
                    .bind(py)
                    .getattr("name")
                    .ok()
                    .and_then(|n| n.extract::<String>().ok())
                    .unwrap_or_else(|| "caller-supplied".to_string())
            });
            let obj = Python::with_gil(|py| tokenizer.clone_ref(py));
            req.budget = Some(Budget {
                max: b,
                metric: BudgetMetric::Tokens,
                tokenizer: Some(Box::new(PyTokenizer { obj, name })),
            });
        }
        Ok(req)
    }
}

/// The transformation engine.
#[pyclass(name = "Engine")]
pub struct PyEngine {
    inner: Engine,
}

#[pymethods]
impl PyEngine {
    #[new]
    fn new() -> Self {
        PyEngine {
            inner: Engine::new(standard_registry()),
        }
    }

    /// Fold raw content using keyword configuration.
    #[pyo3(signature = (
        content,
        profile = "safe",
        path = None,
        language = None,
        allow_lossy = None,
        budget_bytes = None,
        budget_chars = None,
        protected_ranges = None,
        protected_line_markers = None,
    ))]
    #[allow(clippy::too_many_arguments)]
    fn fold(
        &self,
        content: &str,
        profile: &str,
        path: Option<&str>,
        language: Option<&str>,
        allow_lossy: Option<bool>,
        budget_bytes: Option<u64>,
        budget_chars: Option<u64>,
        protected_ranges: Option<Vec<(usize, usize)>>,
        protected_line_markers: Option<Vec<String>>,
    ) -> PyResult<PyFoldResult> {
        let mut req = FoldRequest::new(content);
        req.profile_name = profile.to_string();
        req.path_hint = path.map(|s| s.to_string());
        req.overrides = build_overrides(allow_lossy, protected_ranges, protected_line_markers);
        if let Some(lang) = language {
            req.language = Some(parse_language(lang)?);
        }
        if let Some(b) = budget_bytes {
            req.budget = Some(Budget::bytes(b));
        } else if let Some(b) = budget_chars {
            req.budget = Some(Budget::characters(b));
        }
        self.inner
            .fold(req)
            .map(into_result)
            .map_err(map_engine_error)
    }

    /// Fold a `FoldRequest` object.
    fn fold_request(&self, request: &PyFoldRequest) -> PyResult<PyFoldResult> {
        let req = request.to_core()?;
        self.inner
            .fold(req)
            .map(into_result)
            .map_err(map_engine_error)
    }

    /// Fold the contents of a file. Never writes to disk.
    #[pyo3(signature = (path, profile = "safe", language = None, allow_lossy = None))]
    fn fold_file(
        &self,
        path: &str,
        profile: &str,
        language: Option<&str>,
        allow_lossy: Option<bool>,
    ) -> PyResult<PyFoldResult> {
        let content = std::fs::read_to_string(path)
            .map_err(|e| PyIOError::new_err(format!("failed to read {path}: {e}")))?;
        let mut req = FoldRequest::new(content);
        req.profile_name = profile.to_string();
        req.path_hint = Some(path.to_string());
        req.overrides = build_overrides(allow_lossy, None, None);
        if let Some(lang) = language {
            req.language = Some(parse_language(lang)?);
        }
        self.inner
            .fold(req)
            .map(into_result)
            .map_err(map_engine_error)
    }
}

fn into_result(r: CoreFoldResult) -> PyFoldResult {
    PyFoldResult {
        output: r.output,
        report: r.report,
    }
}

/// Fold content with the default engine.
#[pyfunction]
#[pyo3(signature = (
    content,
    profile = "safe",
    path = None,
    language = None,
    allow_lossy = None,
    budget_bytes = None,
    budget_chars = None,
    protected_ranges = None,
    protected_line_markers = None,
))]
#[allow(clippy::too_many_arguments)]
fn fold(
    content: &str,
    profile: &str,
    path: Option<&str>,
    language: Option<&str>,
    allow_lossy: Option<bool>,
    budget_bytes: Option<u64>,
    budget_chars: Option<u64>,
    protected_ranges: Option<Vec<(usize, usize)>>,
    protected_line_markers: Option<Vec<String>>,
) -> PyResult<PyFoldResult> {
    PyEngine::new().fold(
        content,
        profile,
        path,
        language,
        allow_lossy,
        budget_bytes,
        budget_chars,
        protected_ranges,
        protected_line_markers,
    )
}

/// Fold a file with the default engine.
#[pyfunction]
#[pyo3(signature = (path, profile = "safe", language = None, allow_lossy = None))]
fn fold_file(
    path: &str,
    profile: &str,
    language: Option<&str>,
    allow_lossy: Option<bool>,
) -> PyResult<PyFoldResult> {
    PyEngine::new().fold_file(path, profile, language, allow_lossy)
}

/// Return the list of built-in profile names.
#[pyfunction]
fn profiles() -> Vec<String> {
    Profile::names().iter().map(|s| s.to_string()).collect()
}

/// Return documentation metadata for a profile.
#[pyfunction]
fn profile_info(py: Python<'_>, name: &str) -> PyResult<PyObject> {
    let profile = Profile::named(name).map_err(map_engine_error)?;
    let value = serde_json::to_value(&profile)
        .map_err(|e| ContextFoldError::new_err(format!("failed to serialize profile: {e}")))?;
    Ok(json_to_py(py, &value))
}

/// Detect the language of a path/content pair.
#[pyfunction]
#[pyo3(signature = (content, path = None))]
fn detect_language(content: &str, path: Option<&str>) -> String {
    contextfold_core::detect_language(path, content)
        .as_str()
        .to_string()
}

/// Languages with a structural (Tree-sitter) analyzer.
#[pyfunction]
fn supported_languages() -> Vec<String> {
    let mut langs = vec![
        "markdown".to_string(),
        "log".to_string(),
        "json".to_string(),
        "text".to_string(),
    ];
    langs.extend(
        contextfold_parsers::supported_code_languages()
            .iter()
            .map(|l| l.as_str().to_string()),
    );
    langs
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyEngine>()?;
    m.add_class::<PyFoldRequest>()?;
    m.add_class::<PyFoldResult>()?;
    m.add_class::<PyReport>()?;
    m.add("ContextFoldError", m.py().get_type::<ContextFoldError>())?;
    m.add(
        "UnknownProfileError",
        m.py().get_type::<UnknownProfileError>(),
    )?;
    m.add(
        "InvalidConfigError",
        m.py().get_type::<InvalidConfigError>(),
    )?;
    m.add("BudgetNotMetError", m.py().get_type::<BudgetNotMetError>())?;
    m.add_function(wrap_pyfunction!(fold, m)?)?;
    m.add_function(wrap_pyfunction!(fold_file, m)?)?;
    m.add_function(wrap_pyfunction!(profiles, m)?)?;
    m.add_function(wrap_pyfunction!(profile_info, m)?)?;
    m.add_function(wrap_pyfunction!(detect_language, m)?)?;
    m.add_function(wrap_pyfunction!(supported_languages, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
