//! # contextfold-parsers
//!
//! Tree-sitter parser integration and format detection for PyContextFold.
//!
//! This crate implements [`contextfold_core::LanguageAnalyzer`] for Python,
//! Rust, JavaScript, TypeScript, TSX and Go. It is the only crate that depends
//! on Tree-sitter; the core transformation pipeline stays parser-agnostic.
//!
//! Analyzers are *read-only*: they parse content provided in memory and never
//! touch the filesystem or network.

use contextfold_core::analyzer::{Analysis, Declaration, DeclarationKind, LanguageAnalyzer};
use contextfold_core::lang::{LanguageId, Span};
use contextfold_core::Registry;
use tree_sitter::{Language, Node, Parser};

mod langspec;
use langspec::LangSpec;

/// A Tree-sitter-backed analyzer for one language.
struct TreeSitterAnalyzer {
    spec: LangSpec,
}

impl TreeSitterAnalyzer {
    fn new(spec: LangSpec) -> Self {
        TreeSitterAnalyzer { spec }
    }

    fn parse(&self, source: &str) -> Option<(tree_sitter::Tree, bool)> {
        let mut parser = Parser::new();
        parser.set_language(&self.spec.ts).ok()?;
        let tree = parser.parse(source, None)?;
        let ok = !tree.root_node().has_error();
        Some((tree, ok))
    }
}

impl LanguageAnalyzer for TreeSitterAnalyzer {
    fn language(&self) -> LanguageId {
        self.spec.language_id
    }

    fn extensions(&self) -> &'static [&'static str] {
        self.spec.extensions
    }

    fn analyze(&self, source: &str) -> Analysis {
        let mut analysis = Analysis::empty(self.spec.language_id);
        let Some((tree, ok)) = self.parse(source) else {
            return analysis;
        };
        analysis.parsed = ok;
        if !ok {
            // Still return the (partial) structure? No: conservative callers
            // only use structure when `parsed` is true. Return empty facts.
            analysis.parsed = false;
            return analysis;
        }

        let src = source.as_bytes();
        let mut stack: Vec<Node> = vec![tree.root_node()];
        while let Some(node) = stack.pop() {
            self.visit(node, src, &mut analysis);
            let mut cursor = node.walk();
            let children: Vec<Node> = node.children(&mut cursor).collect();
            // Reverse so traversal order is stable left-to-right.
            for child in children.into_iter().rev() {
                stack.push(child);
            }
        }
        analysis
    }
}

impl TreeSitterAnalyzer {
    fn visit(&self, node: Node, src: &[u8], analysis: &mut Analysis) {
        let kind = node.kind();
        let span = Span::new(node.start_byte(), node.end_byte());

        if self.spec.comment_kinds.contains(&kind) {
            analysis.comment_spans.push(span);
        }
        if kind.contains("string") {
            analysis.string_spans.push(span);
        }
        if self.spec.import_kinds.contains(&kind) {
            analysis.import_spans.push(span);
        }
        if self.spec.error_kinds.contains(&kind) {
            analysis.error_handling_spans.push(span);
        }

        if self.spec.python_docstrings && (kind == "block" || kind == "module") {
            if let Some(doc) = python_docstring_of(node) {
                analysis.docstring_spans.push(doc);
            }
        }

        for (decl_kind, mapped) in self.spec.decl_kinds {
            if kind == *decl_kind {
                if let Some(decl) = self.make_declaration(node, src, *mapped) {
                    analysis.declarations.push(decl);
                }
                break;
            }
        }
    }

    fn make_declaration(
        &self,
        node: Node,
        src: &[u8],
        kind: DeclarationKind,
    ) -> Option<Declaration> {
        let span = Span::new(node.start_byte(), node.end_byte());
        let name = node
            .child_by_field_name("name")
            .and_then(|n| n.utf8_text(src).ok())
            .unwrap_or_default()
            .to_string();
        let body = node.child_by_field_name(self.spec.body_field);
        let elide = self.spec.elide_only.contains(&node.kind());
        match body {
            Some(b) if elide => Some(Declaration {
                kind,
                name,
                span,
                body_start: b.start_byte(),
                body_end: b.end_byte(),
                has_body: true,
            }),
            _ => Some(Declaration {
                kind,
                name,
                span,
                body_start: span.end,
                body_end: span.end,
                has_body: false,
            }),
        }
    }
}

/// Detect a Python docstring: a `block`/`module` whose first named child is an
/// `expression_statement` wrapping a single string. Returns the span of the
/// expression statement so removal leaves valid syntax.
fn python_docstring_of(node: Node) -> Option<Span> {
    let first = node.named_child(0)?;
    if first.kind() != "expression_statement" {
        return None;
    }
    let inner = first.named_child(0)?;
    if inner.kind() == "string" || inner.kind() == "concatenated_string" {
        Some(Span::new(first.start_byte(), first.end_byte()))
    } else {
        None
    }
}

/// Build the standard analyzer registry (all supported code languages).
pub fn standard_registry() -> Registry {
    let mut registry = Registry::new();
    for spec in LangSpec::all() {
        registry = registry.register(TreeSitterAnalyzer::new(spec));
    }
    registry
}

/// Build an [`contextfold_core::Engine`] wired with every supported analyzer.
pub fn standard_engine() -> contextfold_core::Engine {
    contextfold_core::Engine::new(standard_registry())
}

/// The language ids this crate can parse.
pub fn supported_code_languages() -> Vec<LanguageId> {
    LangSpec::all().iter().map(|s| s.language_id).collect()
}

/// Parse `source` for `language` and return the raw Tree-sitter language used.
/// Exposed for tests and tooling.
pub fn ts_language_for(language: LanguageId) -> Option<Language> {
    LangSpec::all()
        .iter()
        .find(|s| s.language_id == language)
        .map(|s| s.ts.clone())
}
