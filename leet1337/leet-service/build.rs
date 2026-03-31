fn main() {
    tonic_build::configure()
        .build_server(true)
        .compile(&["proto/leet.proto"], &["proto"])
        .unwrap();
}
