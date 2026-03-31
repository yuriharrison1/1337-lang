use colored::Colorize;

pub fn run() -> anyhow::Result<()> {
    println!("{}", "leet — 1337 protocol developer tools".bold());
    println!();
    println!("  CLI version  : {}", env!("CARGO_PKG_VERSION").green());
    println!("  leet-core    : 0.4.0");
    println!("  Protocol     : 1337/v1");
    println!("  Dimensions   : 32 canonical axes");
    println!("  Groups       : Ontological (A, 0–13) · Epistemic (B, 14–21) · Pragmatic (C, 22–31)");
    println!();
    println!("  Build info:");
    println!("    Profile  : {}", if cfg!(debug_assertions) { "debug" } else { "release" });
    println!("    Target   : {}", std::env::consts::ARCH);
    println!("    OS       : {}", std::env::consts::OS);

    Ok(())
}
