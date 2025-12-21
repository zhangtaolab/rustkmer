fn main() {
    // Configure for PyO3 extension module
    println!("cargo:rerun-if-env-changed=PYO3_BUILD_CONFIG");
}
