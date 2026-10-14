use contextfold_core::analyzer::DeclarationKind;
use contextfold_core::lang::LanguageId;
use tree_sitter::Language;

/// Per-language configuration for the generic Tree-sitter analyzer.
pub struct LangSpec {
    pub language_id: LanguageId,
    pub ts: Language,
    pub extensions: &'static [&'static str],
    /// Node kinds that represent comments (line and block).
    pub comment_kinds: &'static [&'static str],
    /// Node kinds that represent import/use statements.
    pub import_kinds: &'static [&'static str],
    /// Node kinds that represent error-handling constructs.
    pub error_kinds: &'static [&'static str],
    /// Declaration node kinds and the mapped semantic kind.
    pub decl_kinds: &'static [(&'static str, DeclarationKind)],
    /// Field name holding a declaration's body block.
    pub body_field: &'static str,
    /// Declaration kinds whose bodies may be elided under `interface-only`.
    pub elide_only: &'static [&'static str],
    /// Whether to detect Python triple-quoted docstrings separately.
    pub python_docstrings: bool,
}

impl LangSpec {
    pub fn all() -> Vec<LangSpec> {
        vec![python(), rust(), javascript(), typescript(), tsx(), go()]
    }
}

fn python() -> LangSpec {
    LangSpec {
        language_id: LanguageId::Python,
        ts: tree_sitter_python::LANGUAGE.into(),
        extensions: &["py", "pyi", "pyw"],
        comment_kinds: &["comment"],
        import_kinds: &[
            "import_statement",
            "import_from_statement",
            "future_import_statement",
        ],
        error_kinds: &[
            "try_statement",
            "raise_statement",
            "except_clause",
            "finally_clause",
        ],
        decl_kinds: &[
            ("function_definition", DeclarationKind::Function),
            ("class_definition", DeclarationKind::Class),
        ],
        body_field: "body",
        elide_only: &["function_definition"],
        python_docstrings: true,
    }
}

fn rust() -> LangSpec {
    LangSpec {
        language_id: LanguageId::Rust,
        ts: tree_sitter_rust::LANGUAGE.into(),
        extensions: &["rs"],
        comment_kinds: &["line_comment", "block_comment"],
        import_kinds: &["use_declaration"],
        error_kinds: &["try_expression"],
        decl_kinds: &[
            ("function_item", DeclarationKind::Function),
            ("struct_item", DeclarationKind::Struct),
            ("enum_item", DeclarationKind::Enum),
            ("trait_item", DeclarationKind::Trait),
            ("type_item", DeclarationKind::TypeAlias),
            ("const_item", DeclarationKind::Const),
            ("static_item", DeclarationKind::Static),
            ("mod_item", DeclarationKind::Module),
            ("union_item", DeclarationKind::Struct),
            ("macro_definition", DeclarationKind::Other),
        ],
        body_field: "body",
        elide_only: &["function_item"],
        python_docstrings: false,
    }
}

fn javascript() -> LangSpec {
    LangSpec {
        language_id: LanguageId::JavaScript,
        ts: tree_sitter_javascript::LANGUAGE.into(),
        extensions: &["js", "mjs", "cjs", "jsx"],
        comment_kinds: &["comment"],
        import_kinds: &["import_statement"],
        error_kinds: &["try_statement", "throw_statement"],
        decl_kinds: &[
            ("function_declaration", DeclarationKind::Function),
            ("generator_function_declaration", DeclarationKind::Function),
            ("class_declaration", DeclarationKind::Class),
            ("method_definition", DeclarationKind::Method),
        ],
        body_field: "body",
        elide_only: &[
            "function_declaration",
            "generator_function_declaration",
            "method_definition",
        ],
        python_docstrings: false,
    }
}

fn typescript() -> LangSpec {
    LangSpec {
        language_id: LanguageId::TypeScript,
        ts: tree_sitter_typescript::LANGUAGE_TYPESCRIPT.into(),
        extensions: &["ts", "mts", "cts"],
        comment_kinds: &["comment"],
        import_kinds: &["import_statement"],
        error_kinds: &["try_statement", "throw_statement"],
        decl_kinds: &[
            ("function_declaration", DeclarationKind::Function),
            ("method_definition", DeclarationKind::Method),
            ("class_declaration", DeclarationKind::Class),
            ("abstract_class_declaration", DeclarationKind::Class),
            ("interface_declaration", DeclarationKind::Interface),
            ("type_alias_declaration", DeclarationKind::TypeAlias),
            ("enum_declaration", DeclarationKind::Enum),
        ],
        body_field: "body",
        elide_only: &["function_declaration", "method_definition"],
        python_docstrings: false,
    }
}

fn tsx() -> LangSpec {
    LangSpec {
        language_id: LanguageId::Tsx,
        ts: tree_sitter_typescript::LANGUAGE_TSX.into(),
        extensions: &["tsx"],
        comment_kinds: &["comment"],
        import_kinds: &["import_statement"],
        error_kinds: &["try_statement", "throw_statement"],
        decl_kinds: &[
            ("function_declaration", DeclarationKind::Function),
            ("method_definition", DeclarationKind::Method),
            ("class_declaration", DeclarationKind::Class),
            ("interface_declaration", DeclarationKind::Interface),
            ("type_alias_declaration", DeclarationKind::TypeAlias),
            ("enum_declaration", DeclarationKind::Enum),
        ],
        body_field: "body",
        elide_only: &["function_declaration", "method_definition"],
        python_docstrings: false,
    }
}

fn go() -> LangSpec {
    LangSpec {
        language_id: LanguageId::Go,
        ts: tree_sitter_go::LANGUAGE.into(),
        extensions: &["go"],
        comment_kinds: &["comment"],
        import_kinds: &["import_declaration"],
        // Go has no exceptions; error handling is idiomatic `if err != nil`.
        // It is not detected structurally and is never removed by any profile.
        error_kinds: &[],
        decl_kinds: &[
            ("function_declaration", DeclarationKind::Function),
            ("method_declaration", DeclarationKind::Method),
            ("type_declaration", DeclarationKind::TypeAlias),
            ("const_declaration", DeclarationKind::Const),
            ("var_declaration", DeclarationKind::Static),
        ],
        body_field: "body",
        elide_only: &["function_declaration", "method_declaration"],
        python_docstrings: false,
    }
}
