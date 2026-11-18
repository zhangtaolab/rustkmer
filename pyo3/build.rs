fn main() {
    // Configure for PyO3 extension module
    println!("cargo:rerun-if-env-changed=PYO3_BUILD_CONFIG");

    // Emit the macOS `-undefined dynamic_lookup` cdylib link args that pyo3 0.27
    // no longer emits automatically. The call is intentionally unconditional:
    // `cargo:rustc-cdylib-link-arg` only affects this crate's cdylib link step,
    // and the documented manual build does not enable the `extension-module`
    // cargo feature, so gating on it would leave that path unfixed.
    pyo3_build_config::add_extension_module_link_args();
}
