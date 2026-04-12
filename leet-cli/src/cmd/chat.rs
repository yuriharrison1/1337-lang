//! Interactive 1337 multi-agent chat terminal.
//!
//! Flow:
//!   1. Transmit COGON_ZERO as handshake
//!   2. Loop: read user input → NL→COGON → send to Claude → display agent responses
//!   3. Every 5 rounds print accumulated session statistics

use std::collections::HashMap;
use std::io::{self, BufRead, Write};
use std::time::Instant;

use crossterm::{
    execute,
    style::{Color, ResetColor, SetForegroundColor},
};
use leet_bridge::anthropic_client::{AgentResponse, AnthropicClient, Message};
use leet_bridge::nl_translator::{cogon_to_nl, infer_intent, nl_to_cogon};
use leet_core::{types::RawField, types::RawRole, Cogon};
use leet_service::agent_client::AgentClient;

// ── Agent colors ──────────────────────────────────────────────────────────────

fn agent_color(name: &str) -> Color {
    match name {
        "ATLAS"  => Color::Cyan,
        "CIPHER" => Color::Red,
        "FORGE"  => Color::Yellow,
        "NEXUS"  => Color::Blue,
        "ORACLE" => Color::Magenta,
        "PULSE"  => Color::Green,
        "RAVEN"  => Color::DarkGrey,
        "SPARK"  => Color::DarkYellow,
        "TENSOR" => Color::DarkCyan,
        "VORTEX" => Color::DarkBlue,
        "ZERO"   => Color::White,
        "FLUX"   => Color::DarkGreen,
        "ECHO"   => Color::DarkMagenta,
        "DRIFT"  => Color::DarkRed,
        "PRISM"  => Color::AnsiValue(214), // orange
        _        => Color::White,
    }
}

// ── COGON display ─────────────────────────────────────────────────────────────

/// Compact COGON summary: top activated axes with their values.
///
/// For valence axes (D6, G2, G7, P4, P8) the activation is the deviation from
/// 0.5 so neutral axes don't appear as "significant".
fn cogon_summary(cogon: &Cogon) -> String {
    const AXIS_NAMES: [&str; 32] = [
        "S1","S2","S3","S4","S5","S6","S7","S8",
        "D1","D2","D3","D4","D5","D6","D7","D8",
        "G1","G2","G3","G4","G5","G6","G7","G8",
        "P1","P2","P3","P4","P5","P6","P7","P8",
    ];
    const VALENCE: [usize; 5] = [13, 17, 22, 27, 31]; // D6, G2, G7, P4, P8

    let mut ranked: Vec<(usize, f32, f32)> = cogon
        .sem
        .iter()
        .enumerate()
        .map(|(i, &v)| {
            let activation = if VALENCE.contains(&i) {
                (v - 0.5).abs() * 2.0
            } else {
                v
            };
            (i, v, activation)
        })
        .filter(|(_, _, act)| *act > 0.45)
        .collect();

    ranked.sort_by(|a, b| b.2.partial_cmp(&a.2).unwrap_or(std::cmp::Ordering::Equal));
    ranked.truncate(6);

    if ranked.is_empty() {
        return "[neutral]".to_string();
    }

    let parts: Vec<String> = ranked
        .iter()
        .map(|(i, v, _)| format!("{}:{:.2}", AXIS_NAMES[*i], v))
        .collect();

    format!("[{}]", parts.join(" "))
}

// ── Metrics helpers ───────────────────────────────────────────────────────────

/// Rough token estimate: chars / 3.5 (matches OpenAI/Anthropic averages).
fn estimate_tokens(text: &str) -> usize {
    ((text.len() as f32) / 3.5).ceil() as usize
}

/// COGON binary footprint: sem[32] + unc[32] = 256 bytes.
const COGON_BYTES: usize = 256;

// ── Entry point ───────────────────────────────────────────────────────────────

/// Run the interactive chat loop.
///
/// `lang`       — output language: "pt" (default) or "en"
/// `show_cogon` — if true, display COGON summaries inline
/// `max_agents` — how many agents respond per round (1–6)
pub async fn run(lang: &str, show_cogon: bool, max_agents: usize) {
    let mut out = io::stdout();

    // ── Welcome banner ────────────────────────────────────────────────────
    execute!(out, SetForegroundColor(Color::DarkCyan)).ok();
    let _ = writeln!(out, "╔══════════════════════════════════════════════════════════╗");
    let _ = writeln!(out, "║          LEET CHAT — 1337 MULTI-AGENT TERMINAL           ║");
    let _ = writeln!(out, "╚══════════════════════════════════════════════════════════╝");
    execute!(out, ResetColor).ok();

    execute!(out, SetForegroundColor(Color::DarkGrey)).ok();
    let _ = writeln!(
        out,
        " Agents: ATLAS CIPHER FORGE NEXUS ORACLE PULSE RAVEN SPARK TENSOR VORTEX ZERO FLUX ECHO DRIFT PRISM"
    );
    let _ = writeln!(
        out,
        " Language: {}  |  Show COGON: {}  |  Type 'exit' to quit\n",
        lang, show_cogon
    );
    execute!(out, ResetColor).ok();

    // ── Connect to Anthropic ──────────────────────────────────────────────
    execute!(out, SetForegroundColor(Color::DarkGrey)).ok();
    let _ = write!(out, " Connecting to Anthropic...");
    let _ = out.flush();
    execute!(out, ResetColor).ok();

    let client = match AnthropicClient::new() {
        Ok(c) => {
            execute!(out, SetForegroundColor(Color::Green)).ok();
            let _ = writeln!(out, " OK");
            execute!(out, ResetColor).ok();
            c
        }
        Err(e) => {
            execute!(out, SetForegroundColor(Color::Red)).ok();
            let _ = writeln!(out, " FAILED: {}", e);
            let _ = writeln!(out, " Export LEET_API_KEY and retry.");
            execute!(out, ResetColor).ok();
            return;
        }
    };

    // ── COGON_ZERO handshake ──────────────────────────────────────────────
    let cogon_zero = Cogon::zero();
    execute!(out, SetForegroundColor(Color::DarkGreen)).ok();
    let _ = writeln!(out, " COGON_ZERO transmitted ✓");
    if show_cogon {
        let _ = writeln!(out, " {}", cogon_summary(&cogon_zero));
    }
    execute!(out, ResetColor).ok();
    execute!(out, SetForegroundColor(Color::DarkGrey)).ok();
    let _ = writeln!(out, "────────────────────────────────────────────────────────────");
    execute!(out, ResetColor).ok();

    // ── Session state ─────────────────────────────────────────────────────
    let mut history: Vec<Message> = Vec::new();
    let mut round: usize = 0;
    let mut total_nl_tokens: usize = 0;
    let mut total_cogon_bytes: usize = 0;
    let mut total_latency_ms: u128 = 0;
    let mut agent_counts: HashMap<String, usize> = HashMap::new();

    let stdin = io::stdin();

    // ── Main loop ─────────────────────────────────────────────────────────
    loop {
        // Prompt
        execute!(out, SetForegroundColor(Color::DarkYellow)).ok();
        let _ = write!(out, "\n YURI › ");
        execute!(out, ResetColor).ok();
        let _ = out.flush();

        let mut input = String::new();
        match stdin.lock().read_line(&mut input) {
            Ok(0) => break, // EOF (Ctrl-D)
            Err(_) => break,
            _ => {}
        }
        let input = input.trim().to_string();
        if input.is_empty() {
            continue;
        }
        if input.eq_ignore_ascii_case("exit") || input.eq_ignore_ascii_case("quit") {
            break;
        }

        let start = Instant::now();

        // NL → COGON
        let mut cogon = nl_to_cogon(&input, lang);
        let _intent = infer_intent(&input);

        // Attach original text as raw.content so Claude has full context
        cogon.raw = Some(RawField {
            content_type: "text/plain".to_string(),
            content: serde_json::Value::String(input.clone()),
            role: RawRole::Bridge,
        });

        // User metrics
        let nl_tokens = estimate_tokens(&input);
        total_nl_tokens += nl_tokens;
        total_cogon_bytes += COGON_BYTES;

        if show_cogon {
            execute!(out, SetForegroundColor(Color::DarkGrey)).ok();
            let _ = writeln!(out, "  COGON: {}", cogon_summary(&cogon));
            execute!(out, ResetColor).ok();
        }

        let nl_chars = input.len();
        let cogon_ratio = if nl_chars > 0 {
            COGON_BYTES as f32 / nl_chars as f32
        } else {
            f32::INFINITY
        };
        let ratio_label = if cogon_ratio <= 1.0 {
            format!("{:.1}x compressed", 1.0 / cogon_ratio)
        } else {
            format!("{:.1}x NL size", cogon_ratio)
        };
        execute!(out, SetForegroundColor(Color::DarkGrey)).ok();
        let _ = writeln!(
            out,
            "  ↳ ~{} tokens | {}B NL | {}B COGON | {}",
            nl_tokens, nl_chars, COGON_BYTES, ratio_label
        );
        execute!(out, ResetColor).ok();

        // Push to history (keep last 20 turns)
        let cogon_json = serde_json::to_string(&cogon).unwrap_or_default();
        history.push(Message {
            role: "user".to_string(),
            content: format!("INPUT_COGON:\n{}\nUSER_TEXT: {}", cogon_json, input),
        });
        // Keep last 4 turns (2 user + 2 assistant) to minimize input tokens
        if history.len() > 4 {
            history.drain(0..(history.len() - 4));
        }

        // API call
        let _ = writeln!(out, "");
        let responses: Vec<AgentResponse> = match client.send_cogon(&cogon, &history, max_agents).await {
            Ok(r) => r,
            Err(e) => {
                execute!(out, SetForegroundColor(Color::Red)).ok();
                let _ = writeln!(out, "  API ERROR: {}", e);
                execute!(out, ResetColor).ok();
                history.pop(); // remove failed turn from history
                continue;
            }
        };

        let latency = start.elapsed();
        total_latency_ms += latency.as_millis();
        round += 1;

        // Display agent responses
        let mut response_text = String::new();
        for resp in &responses {
            *agent_counts.entry(resp.agent.clone()).or_insert(0) += 1;

            let color = agent_color(&resp.agent);
            execute!(out, SetForegroundColor(color)).ok();
            let _ = write!(out, "  {:6}  ", resp.agent);
            execute!(out, ResetColor).ok();

            let nl = if lang.starts_with("en") { &resp.nl_en } else { &resp.nl_pt };
            let _ = writeln!(out, "\"{}\"", nl);
            response_text.push_str(nl);
            response_text.push(' ');

            if show_cogon {
                execute!(out, SetForegroundColor(Color::DarkGrey)).ok();
                let _ = writeln!(out, "          {}", cogon_summary(&resp.cogon));
                execute!(out, ResetColor).ok();
            }
        }

        // Throughput = response tokens / elapsed seconds
        let resp_tokens = estimate_tokens(&response_text);
        let throughput = if latency.as_secs_f32() > 0.0 {
            resp_tokens as f32 / latency.as_secs_f32()
        } else {
            0.0
        };

        execute!(out, SetForegroundColor(Color::DarkGrey)).ok();
        let _ = writeln!(
            out,
            "\n  latency: {}ms | ~{:.0} tok/s | {} agent(s) responded",
            latency.as_millis(),
            throughput,
            responses.len()
        );
        execute!(out, ResetColor).ok();

        // Store assistant turn in history (simplified — NL only)
        let assistant_content: Vec<serde_json::Value> = responses
            .iter()
            .map(|r| {
                serde_json::json!({
                    "agent": r.agent,
                    "intent": format!("{:?}", r.intent),
                    "nl_pt": r.nl_pt,
                    "nl_en": r.nl_en,
                })
            })
            .collect();
        history.push(Message {
            role: "assistant".to_string(),
            content: serde_json::to_string(&assistant_content).unwrap_or_default(),
        });

        execute!(out, SetForegroundColor(Color::DarkGrey)).ok();
        let _ = writeln!(out, "────────────────────────────────────────────────────────────");
        execute!(out, ResetColor).ok();

        // ── Every 5 rounds: session summary ──────────────────────────────
        if round % 5 == 0 {
            let avg_latency = if round > 0 { total_latency_ms / round as u128 } else { 0 };
            // total_cogon_bytes is always rounds * 256B (fixed)
            // compare against accumulated NL character count
            let nl_chars_total = history
                .iter()
                .filter(|m| m.role == "user")
                .map(|m| m.content.len())
                .sum::<usize>();
            let ratio = if nl_chars_total > 0 {
                total_cogon_bytes as f32 / nl_chars_total as f32
            } else { 1.0 };
            let ratio_str = if ratio <= 1.0 {
                format!("{:.1}x compressed vs NL", 1.0 / ratio)
            } else {
                format!("{:.1}x NL size (short inputs)", ratio)
            };

            execute!(out, SetForegroundColor(Color::DarkCyan)).ok();
            let _ = writeln!(out, "\n ━━ SESSION STATS (round {}) ━━", round);
            let _ = writeln!(
                out,
                "  NL tokens: {} | COGON bytes: {} | {}",
                total_nl_tokens, total_cogon_bytes, ratio_str
            );
            let _ = writeln!(out, "  Avg latency: {}ms | Rounds: {}", avg_latency, round);

            let mut counts: Vec<(&String, &usize)> = agent_counts.iter().collect();
            counts.sort_by(|a, b| b.1.cmp(a.1));
            let top: Vec<String> = counts
                .iter()
                .take(5)
                .map(|(name, count)| format!("{}({})", name, count))
                .collect();
            let _ = writeln!(out, "  Most active: {}", top.join(" > "));
            execute!(out, ResetColor).ok();
            let _ = writeln!(out, "");
        }
    }

    // ── Farewell ──────────────────────────────────────────────────────────
    let _ = writeln!(out, "");
    execute!(out, SetForegroundColor(Color::DarkCyan)).ok();
    let _ = writeln!(
        out,
        " Chat ended. {} rounds | {} unique agents | {}ms avg latency",
        round,
        agent_counts.len(),
        if round > 0 { total_latency_ms / round as u128 } else { 0 }
    );
    execute!(out, ResetColor).ok();
}

// ── Server-connected mode ─────────────────────────────────────────────────────

/// Chat via a running leet-server instead of calling the Anthropic API directly.
///
/// The CLI connects as the "YURI" agent, sends NL messages to the server,
/// and displays responses received from other agents in the network.
pub async fn run_connected(server_addr: &str, lang: &str, show_cogon: bool) {
    let mut out = io::stdout();

    execute!(out, SetForegroundColor(Color::DarkCyan)).ok();
    let _ = writeln!(out, "╔══════════════════════════════════════════════════════════╗");
    let _ = writeln!(out, "║       LEET CHAT — CONNECTED TO LEET-SERVER               ║");
    let _ = writeln!(out, "╚══════════════════════════════════════════════════════════╝");
    execute!(out, ResetColor).ok();

    execute!(out, SetForegroundColor(Color::DarkGrey)).ok();
    let _ = writeln!(out, " Server: {}  |  Language: {}  |  Type 'exit' to quit", server_addr, lang);
    execute!(out, ResetColor).ok();

    // Connect as YURI (human agent)
    execute!(out, SetForegroundColor(Color::DarkGrey)).ok();
    let _ = write!(out, " Connecting to {} as YURI...", server_addr);
    let _ = out.flush();
    execute!(out, ResetColor).ok();

    let mut client = AgentClient::new(uuid::Uuid::new_v4(), "YURI", "Human user");
    if let Err(e) = client.connect(server_addr).await {
        execute!(out, SetForegroundColor(Color::Red)).ok();
        let _ = writeln!(out, " FAILED: {}", e);
        execute!(out, ResetColor).ok();
        return;
    }

    execute!(out, SetForegroundColor(Color::Green)).ok();
    let _ = writeln!(out, " OK (id={})", client.id);
    execute!(out, ResetColor).ok();

    execute!(out, SetForegroundColor(Color::DarkGrey)).ok();
    let _ = writeln!(out, "────────────────────────────────────────────────────────────");
    execute!(out, ResetColor).ok();

    let stdin = io::stdin();
    let mut round = 0usize;

    loop {
        // Show connected-mode prompt
        execute!(out, SetForegroundColor(Color::DarkYellow)).ok();
        let _ = write!(out, "\n YURI › ");
        execute!(out, ResetColor).ok();
        let _ = out.flush();

        let mut input = String::new();
        match stdin.lock().read_line(&mut input) {
            Ok(0) => break,
            Err(_) => break,
            _ => {}
        }
        let input = input.trim().to_string();
        if input.is_empty() { continue; }
        if input.eq_ignore_ascii_case("exit") || input.eq_ignore_ascii_case("quit") { break; }

        let start = std::time::Instant::now();

        // Display sent COGON if requested
        if show_cogon {
            let cogon = nl_to_cogon(&input, lang);
            execute!(out, SetForegroundColor(Color::DarkGrey)).ok();
            let _ = writeln!(out, "  COGON: {}", cogon_summary(&cogon));
            execute!(out, ResetColor).ok();
        }

        // Send to server
        if let Err(e) = client.send_nl(&input).await {
            execute!(out, SetForegroundColor(Color::Red)).ok();
            let _ = writeln!(out, "  SEND ERROR: {}", e);
            execute!(out, ResetColor).ok();
            continue;
        }

        round += 1;

        // Read responses with 4s timeout between messages
        let _ = writeln!(out, "");
        let mut got_response = false;
        loop {
            match client.recv_timeout(std::time::Duration::from_millis(800)).await {
                Ok(Some(msg)) => {
                    got_response = true;
                    // Extract sender info from the message
                    let nl = if let leet_core::types::Payload::Cogon(ref cogon) = msg.payload {
                        cogon.raw.as_ref()
                            .and_then(|r| r.content.as_str().map(|s| s.to_string()))
                            .unwrap_or_else(|| cogon_to_nl(cogon, lang))
                    } else {
                        "[DAG payload]".to_string()
                    };

                    let agent_label = format!("{:?}", msg.sender).chars().take(8).collect::<String>();
                    execute!(out, SetForegroundColor(Color::Cyan)).ok();
                    let _ = write!(out, "  {:6}  ", &agent_label[..agent_label.len().min(6)]);
                    execute!(out, ResetColor).ok();
                    let _ = writeln!(out, "\"{}\"", nl);

                    if show_cogon {
                        if let leet_core::types::Payload::Cogon(ref c) = msg.payload {
                            execute!(out, SetForegroundColor(Color::DarkGrey)).ok();
                            let _ = writeln!(out, "          {}", cogon_summary(c));
                            execute!(out, ResetColor).ok();
                        }
                    }
                }
                Ok(None) => { break; } // server closed
                Err(_) => { break; }   // timeout — no more messages this round
            }
        }

        let latency = start.elapsed();
        if got_response {
            execute!(out, SetForegroundColor(Color::DarkGrey)).ok();
            let _ = writeln!(out, "\n  latency: {}ms", latency.as_millis());
            execute!(out, ResetColor).ok();
        }

        execute!(out, SetForegroundColor(Color::DarkGrey)).ok();
        let _ = writeln!(out, "────────────────────────────────────────────────────────────");
        execute!(out, ResetColor).ok();
    }

    let _ = writeln!(out, "");
    execute!(out, SetForegroundColor(Color::DarkCyan)).ok();
    let _ = writeln!(out, " Disconnected from {}. {} rounds.", server_addr, round);
    execute!(out, ResetColor).ok();
}
