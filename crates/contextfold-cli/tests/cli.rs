use std::io::Write;
use std::process::{Command, Stdio};

const BIN: &str = env!("CARGO_BIN_EXE_contextfold");

fn run_stdin(args: &[&str], input: &str) -> (String, String, i32) {
    let mut child = Command::new(BIN)
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn");
    child
        .stdin
        .as_mut()
        .unwrap()
        .write_all(input.as_bytes())
        .unwrap();
    let out = child.wait_with_output().unwrap();
    (
        String::from_utf8_lossy(&out.stdout).to_string(),
        String::from_utf8_lossy(&out.stderr).to_string(),
        out.status.code().unwrap_or(-1),
    )
}

#[test]
fn stdin_safe_profile() {
    let (stdout, _stderr, code) = run_stdin(&["-p", "safe", "-L", "python"], "# c\nx = 1\n");
    assert_eq!(code, 0);
    assert_eq!(stdout, "x = 1\n");
}

#[test]
fn stdin_default_profile_is_safe() {
    let (stdout, _stderr, code) = run_stdin(&["-L", "python", "--quiet"], "# c\nx = 1\n");
    assert_eq!(code, 0);
    assert_eq!(stdout, "x = 1\n");
}

#[test]
fn unknown_profile_is_rejected() {
    let (_stdout, _stderr, code) = run_stdin(&["-p", "nope"], "x = 1\n");
    assert_ne!(code, 0);
}

#[test]
fn report_json_is_written() {
    let dir = std::env::temp_dir().join(format!("pcf-cli-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let report = dir.join("report.json");
    let (stdout, _stderr, code) = run_stdin(
        &[
            "-p",
            "safe",
            "-L",
            "python",
            "--report",
            report.to_str().unwrap(),
            "--quiet",
        ],
        "# c\nx = 1\n\n\n\ny = 2\n",
    );
    assert_eq!(code, 0);
    assert!(!stdout.contains("# c"));
    let text = std::fs::read_to_string(&report).unwrap();
    let value: serde_json::Value = serde_json::from_str(&text).unwrap();
    assert_eq!(value["profile"], "safe");
    assert_eq!(value["semantic_equivalence"], "not_guaranteed");
    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn multiple_inputs_without_output_dir_is_error() {
    let dir = std::env::temp_dir().join(format!("pcf-cli-multi-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let a = dir.join("a.py");
    let b = dir.join("b.py");
    std::fs::write(&a, "# a\nx = 1\n").unwrap();
    std::fs::write(&b, "# b\ny = 1\n").unwrap();
    let out = Command::new(BIN)
        .args([a.to_str().unwrap(), b.to_str().unwrap(), "--quiet"])
        .output()
        .unwrap();
    assert_ne!(out.status.code().unwrap_or(-1), 0);
    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn in_place_overwrites_input() {
    let dir = std::env::temp_dir().join(format!("pcf-cli-inplace-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let file = dir.join("a.py");
    std::fs::write(&file, "# comment\nx = 1\n").unwrap();
    let out = Command::new(BIN)
        .args([
            file.to_str().unwrap(),
            "--in-place",
            "-p",
            "safe",
            "--quiet",
        ])
        .output()
        .unwrap();
    assert_eq!(out.status.code().unwrap_or(-1), 0);
    let written = std::fs::read_to_string(&file).unwrap();
    assert!(!written.contains("# comment"));
    assert!(written.contains("x = 1"));
    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn output_dir_writes_all_inputs() {
    let dir = std::env::temp_dir().join(format!("pcf-cli-outdir-{}", std::process::id()));
    let outdir = dir.join("out");
    std::fs::create_dir_all(&outdir).unwrap();
    let a = dir.join("a.py");
    let b = dir.join("b.py");
    std::fs::write(&a, "# a\nx = 1\n").unwrap();
    std::fs::write(&b, "# b\ny = 1\n").unwrap();
    let status = Command::new(BIN)
        .args([
            a.to_str().unwrap(),
            b.to_str().unwrap(),
            "--output-dir",
            outdir.to_str().unwrap(),
            "--quiet",
        ])
        .status()
        .unwrap();
    assert!(status.success());
    assert!(outdir.join("a.py").exists());
    assert!(outdir.join("b.py").exists());
    let a_out = std::fs::read_to_string(outdir.join("a.py")).unwrap();
    assert!(!a_out.contains("# a"));
    std::fs::remove_dir_all(&dir).ok();
}
