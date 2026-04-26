//! Smoke test — spawns leet-mcp as a subprocess, pipes JSON-RPC, verifies.

use std::io::Write;
use std::process::{Command, Stdio};

#[test]
fn initialize_and_list_tools() {
    let bin = env!("CARGO_BIN_EXE_leet-mcp");

    let tmp = tempfile::tempdir().expect("tempdir");
    let mut child = Command::new(bin)
        .current_dir(tmp.path())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn leet-mcp");

    let stdin = child.stdin.as_mut().unwrap();
    writeln!(
        stdin,
        r#"{{"jsonrpc":"2.0","id":1,"method":"initialize","params":{{}}}}"#
    )
    .unwrap();
    writeln!(
        stdin,
        r#"{{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{{}}}}"#
    )
    .unwrap();
    stdin.flush().unwrap();
    drop(child.stdin.take());

    let output = child.wait_with_output().expect("wait");
    let stdout = String::from_utf8_lossy(&output.stdout);

    assert!(stdout.contains("leet-mcp"), "missing serverInfo.name");
    assert!(stdout.contains("leet_recall"), "missing leet_recall tool");
    assert!(stdout.contains("leet_remember"), "missing leet_remember tool");
}
