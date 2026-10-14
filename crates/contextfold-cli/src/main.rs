//! Standalone CLI for PyContextFold.
//!
//! Reads content from files or stdin, applies a named profile, writes the
//! transformed content to a destination (never overwriting inputs unless
//! `--in-place` is given) and can emit a machine-readable JSON report.

use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use clap::Parser;
use contextfold_core::model::{FoldRequest, FoldResult};
use contextfold_core::profile::Profile;
use contextfold_core::tokenizer::Budget;
use contextfold_core::{Engine, LanguageId};
use contextfold_parsers::standard_engine;

#[derive(Parser, Debug)]
#[command(
    name = "contextfold",
    version,
    about = "Structure-aware context optimization for LLM consumption.",
    long_about = "PyContextFold transforms source code, documentation, logs and structured \
text into compact representations. It is local-first and deterministic: it never sends \
content to external services and never overwrites inputs unless --in-place is given."
)]
struct Cli {
    /// Input files. Use `-` or omit for stdin. Multiple files require --output-dir.
    #[arg(value_name = "INPUT")]
    inputs: Vec<PathBuf>,

    /// Named transformation profile.
    #[arg(short, long, default_value = "safe", value_parser = profile_names())]
    profile: String,

    /// Override detected language (e.g. python, rust, typescript, markdown, logs).
    #[arg(short = 'L', long)]
    language: Option<String>,

    /// Write transformed output to this file (single input only).
    #[arg(short, long, conflicts_with = "output_dir")]
    output: Option<PathBuf>,

    /// Write transformed outputs into this directory (multiple inputs).
    #[arg(long, value_name = "DIR")]
    output_dir: Option<PathBuf>,

    /// Overwrite each input file in place. Requires explicit opt-in.
    #[arg(long, conflicts_with_all = ["output", "output_dir"])]
    in_place: bool,

    /// Write a JSON transformation report to this file.
    #[arg(long, value_name = "FILE")]
    report: Option<PathBuf>,

    /// Target budget in UTF-8 bytes (an approximation, never reported as tokens).
    #[arg(long, conflicts_with = "budget_chars")]
    budget_bytes: Option<u64>,

    /// Target budget in Unicode characters (an approximation, never tokens).
    #[arg(long)]
    budget_chars: Option<u64>,

    /// Permit explicitly lossy transformations (interface-only, log collapsing).
    #[arg(long)]
    allow_lossy: bool,

    /// Suppress the human-readable summary on stderr.
    #[arg(short, long)]
    quiet: bool,
}

fn profile_names() -> clap::builder::PossibleValuesParser {
    clap::builder::PossibleValuesParser::new(Profile::names().iter().copied())
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    match run(&cli) {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("error: {e}");
            ExitCode::FAILURE
        }
    }
}

fn run(cli: &Cli) -> Result<(), String> {
    let engine = standard_engine();

    let use_stdin = cli.inputs.is_empty() || cli.inputs == [PathBuf::from("-")];
    if cli.inputs.iter().any(|p| p == Path::new("-")) && cli.inputs.len() > 1 {
        return Err("cannot mix stdin ('-') with file inputs".to_string());
    }
    if cli.inputs.len() > 1 && cli.output_dir.is_none() && !cli.in_place {
        return Err("multiple inputs require --output-dir (or --in-place)".to_string());
    }
    if cli.in_place && use_stdin {
        return Err("--in-place cannot be used with stdin".to_string());
    }
    if let Some(dir) = &cli.output_dir {
        if !dir.is_dir() {
            return Err(format!(
                "--output-dir is not a directory: {}",
                dir.display()
            ));
        }
    }

    if use_stdin {
        let mut content = String::new();
        std::io::stdin()
            .read_to_string(&mut content)
            .map_err(|e| format!("failed to read stdin: {e}"))?;
        let result = fold(&engine, &content, None, cli)?;
        write_out(cli.output.as_deref(), result.output.as_bytes())?;
        emit_report(cli, std::slice::from_ref(&result))?;
        return Ok(());
    }

    let mut results: Vec<FoldResult> = Vec::with_capacity(cli.inputs.len());
    for input in &cli.inputs {
        let content = std::fs::read_to_string(input)
            .map_err(|e| format!("failed to read {}: {e}", input.display()))?;
        let result = fold(&engine, &content, Some(input), cli)?;
        let dest: Option<PathBuf> = if cli.in_place {
            Some(input.clone())
        } else if let Some(dir) = &cli.output_dir {
            let name = input
                .file_name()
                .ok_or_else(|| format!("invalid input path: {}", input.display()))?;
            Some(dir.join(name))
        } else {
            cli.output.clone()
        };
        write_out(dest.as_deref(), result.output.as_bytes())?;
        results.push(result);
    }
    emit_report(cli, &results)?;
    Ok(())
}

fn fold(
    engine: &Engine,
    content: &str,
    path: Option<&Path>,
    cli: &Cli,
) -> Result<FoldResult, String> {
    let mut req = FoldRequest::new(content);
    if let Some(p) = path {
        req.path_hint = Some(p.to_string_lossy().to_string());
    }
    req.profile_name = cli.profile.clone();
    if cli.allow_lossy {
        req.overrides.allow_lossy = Some(true);
    }
    if let Some(lang) = &cli.language {
        req.language = Some(parse_language(lang)?);
    }
    if let Some(b) = cli.budget_bytes {
        req.budget = Some(Budget::bytes(b));
    } else if let Some(b) = cli.budget_chars {
        req.budget = Some(Budget::characters(b));
    }
    engine
        .fold(req)
        .map_err(|e| format!("transformation failed: {e}"))
}

fn emit_report(cli: &Cli, results: &[FoldResult]) -> Result<(), String> {
    if let Some(path) = &cli.report {
        let json = if results.len() == 1 {
            serde_json::to_string_pretty(&results[0].report)
        } else {
            let reports: Vec<_> = results.iter().map(|r| &r.report).collect();
            serde_json::to_string_pretty(&reports)
        }
        .map_err(|e| format!("failed to serialize report: {e}"))?;
        std::fs::write(path, json).map_err(|e| format!("failed to write report: {e}"))?;
    }
    if !cli.quiet {
        for r in results {
            eprintln!(
                "{} [{}] {} -> {} bytes ({:.1}% reduction), syntax_valid={:?}, behavior_preserving={}",
                r.report.detected_language,
                r.report.profile,
                r.report.input.bytes,
                r.report.output.bytes,
                r.report.reduction_ratio * 100.0,
                r.report.syntax_valid,
                r.report.behavior_preserving,
            );
            for w in &r.report.warnings {
                eprintln!("  warning [{}]: {}", w.code, w.message);
            }
        }
    }
    Ok(())
}

fn parse_language(name: &str) -> Result<LanguageId, String> {
    use LanguageId::*;
    let l = match name.to_ascii_lowercase().as_str() {
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
        other => return Err(format!("unknown language: {other}")),
    };
    Ok(l)
}

fn write_out(path: Option<&Path>, content: &[u8]) -> Result<(), String> {
    match path {
        Some(p) if p != Path::new("-") => {
            std::fs::write(p, content).map_err(|e| format!("failed to write {}: {e}", p.display()))
        }
        _ => std::io::stdout()
            .write_all(content)
            .map_err(|e| format!("failed to write stdout: {e}")),
    }
}
