use colored::Colorize;
use leet_core::axes::{AxisGroup, CANONICAL_AXES};
use leet_core::types::Cogon;
use std::path::Path;

pub fn run(cogon_arg: &str) -> anyhow::Result<()> {
    // Determine source: file path or inline JSON
    let json_str = if Path::new(cogon_arg).exists() {
        std::fs::read_to_string(cogon_arg)?
    } else {
        cogon_arg.to_string()
    };

    let cogon: Cogon = serde_json::from_str(&json_str)?;

    println!("{}", "COGON Inspection Report".bold());
    println!("ID    : {}", cogon.id);
    println!("Stamp : {}", cogon.stamp);
    println!();

    // Structural validation
    println!("{}", "Validation:".bold());
    let sem_ok = cogon.sem.len() == 32;
    let unc_ok = cogon.unc.len() == 32;
    println!("  sem length == 32  : {}", if sem_ok { "OK".green() } else { "FAIL".red() });
    println!("  unc length == 32  : {}", if unc_ok { "OK".green() } else { "FAIL".red() });

    if sem_ok {
        let sem_range_ok = cogon.sem.iter().all(|&v| (0.0..=1.0).contains(&v));
        println!(
            "  sem values in [0,1]: {}",
            if sem_range_ok { "OK".green() } else { "FAIL".red() }
        );
    }
    if unc_ok {
        let unc_range_ok = cogon.unc.iter().all(|&v| (0.0..=1.0).contains(&v));
        println!(
            "  unc values in [0,1]: {}",
            if unc_range_ok { "OK".green() } else { "FAIL".red() }
        );

        // R5 warning — high uncertainty
        let high_unc: Vec<usize> = cogon
            .unc
            .iter()
            .enumerate()
            .filter(|(_, &u)| u > 0.9)
            .map(|(i, _)| i)
            .collect();
        if !high_unc.is_empty() {
            println!(
                "  {}  axes with unc > 0.9: {:?}",
                "R5 WARNING:".yellow().bold(),
                high_unc
            );
        } else {
            println!("  R5 check (unc > 0.9) : {}", "no warnings".green());
        }
    }
    println!();

    // Group averages
    if sem_ok {
        println!("{}", "Group averages:".bold());
        let avg_a: f32 =
            cogon.sem[0..14].iter().sum::<f32>() / 14.0;
        let avg_b: f32 =
            cogon.sem[14..22].iter().sum::<f32>() / 8.0;
        let avg_c: f32 =
            cogon.sem[22..32].iter().sum::<f32>() / 10.0;
        println!("  {} (Ontological, 0–13) : {:.3}", "Group A".blue().bold(), avg_a);
        println!("  {} (Epistemic,   14–21): {:.3}", "Group B".cyan().bold(), avg_b);
        println!("  {} (Pragmatic,   22–31): {:.3}", "Group C".green().bold(), avg_c);
        println!();
    }

    // Dominant axes: sem > 0.7 and unc < 0.4
    if sem_ok && unc_ok {
        println!("{}", "Dominant axes (sem > 0.7, unc < 0.4):".bold());
        let mut found = false;
        for axis in CANONICAL_AXES.iter() {
            let i = axis.index;
            if cogon.sem[i] > 0.7 && cogon.unc[i] < 0.4 {
                let group_label = match axis.group {
                    AxisGroup::Ontological => "A",
                    AxisGroup::Epistemic => "B",
                    AxisGroup::Pragmatic => "C",
                };
                println!(
                    "  [{}][{:2}] {:<22}: sem={:.3}  unc={:.3}",
                    group_label, i, axis.name, cogon.sem[i], cogon.unc[i]
                );
                found = true;
            }
        }
        if !found {
            println!("  (none)");
        }
        println!();
    }

    // Full vector display
    println!("{}", "Full vector:".bold());
    for axis in CANONICAL_AXES.iter() {
        let i = axis.index;
        let label = match axis.group {
            AxisGroup::Ontological => format!("[{:2}] {:<22}", i, axis.name).blue().to_string(),
            AxisGroup::Epistemic => format!("[{:2}] {:<22}", i, axis.name).cyan().to_string(),
            AxisGroup::Pragmatic => format!("[{:2}] {:<22}", i, axis.name).green().to_string(),
        };
        if sem_ok && unc_ok {
            println!("  {} : sem={:.3}  unc={:.3}", label, cogon.sem[i], cogon.unc[i]);
        }
    }

    Ok(())
}
