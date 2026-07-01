//! CJK string-literal gate (FOUND-04, D-07).
//!
//! Parses every `.rs` file in `src/` (excluding `src/cli/`) and `pyo3/src/`
//! (excluding the git-tracked-but-not-compiled dead files) with `syn::parse_file`
//! and asserts that NO source-level string literal contains a covered CJK code
//! point (Han + Hiragana + Katakana + Hangul). Emoji and Latin are allowed.
//!
//! ## Why BOTH `visit_lit` and `visit_macro`
//!
//! A `visit_lit`-only visitor catches bare string literals (`let s = "...";`) but
//! SILENTLY MISSES every CJK literal embedded as a `println!`/`format!`/`log::*!`
//! macro argument — because syn parses macro argument tokens as `TokenStream`, not
//! as a `Lit::Str` AST node. Without `visit_macro`, all 51 CJK strings inside
//! `log::info!`/`log::error!` calls in `src/database/prefix_cache_merge.rs` would
//! be invisible to this gate (RESEARCH.md §1, empirically verified).
//!
//! ## Out of scope
//!
//! - `src/cli/**` — FOUND-04 boundary exempts CLI output.
//! - Dead pyo3 files (`*_backup*`, `*new_approaches*`, `*stage1_fix_backup*`) —
//!   git-tracked but not compiled; translating them is wasted effort.
//! - Code comments — syn discards comments during parsing, so they are naturally
//!   ignored (out of scope per SPEC boundary; deferred).

#![allow(clippy::needless_borrow)]

use std::path::{Path, PathBuf};

use proc_macro2::TokenTree;
use syn::{visit::Visit, Lit, Macro};
use walkdir::WalkDir;

/// Per-file hit record: (file path, 1-based line, offending literal value).
type Hit = (PathBuf, usize, String);

struct CjkLiteralScanner {
    /// Path of the file currently being walked (set per `visit_file`).
    current_file: PathBuf,
    /// Source text of the file currently being walked (for line lookup).
    current_source: String,
    /// Accumulated hits across the whole scan.
    hits: Vec<Hit>,
    /// True while walking inside a `#[doc = "..."]` attribute (rustc desugars
    /// `///` and `//!` comments into these). Per SPEC boundary, CODE COMMENTS
    /// are out of scope — only runtime string literals are gated — so doc
    /// attribute literals must be skipped. Without this, every `/// 中文` doc
    /// comment would false-positive as a CJK string literal.
    in_doc_attr_stack: Vec<bool>,
}

impl<'ast> Visit<'ast> for CjkLiteralScanner {
    /// Track entry into `#[doc = "..."]` attributes so the contained literal
    /// is treated as a comment, not a runtime string.
    fn visit_attribute(&mut self, i: &'ast syn::Attribute) {
        let is_doc = i.path().is_ident("doc");
        if is_doc {
            self.in_doc_attr_stack.push(true);
        }
        syn::visit::visit_attribute(self, i);
        if is_doc {
            self.in_doc_attr_stack.pop();
        }
    }

    /// Catches bare string literals: `let s = "...";`, raw strings, mixed.
    /// Skips literals inside `#[doc = "..."]` attributes (they are comments).
    fn visit_lit(&mut self, i: &'ast Lit) {
        let inside_doc = self.in_doc_attr_stack.last().copied().unwrap_or(false);
        if !inside_doc {
            if let Lit::Str(ls) = i {
                let val = ls.value();
                if contains_cjk(&val) {
                    let line = locate_line(&self.current_source, &val);
                    self.hits
                        .push((self.current_file.clone(), line, val.clone()));
                }
            }
        }
        syn::visit::visit_lit(self, i);
    }

    /// Catches string literals inside macro arguments: `println!("...")`,
    /// `format!("... {}"), eprintln!("..."), `log::info!("..."), etc.
    ///
    /// syn parses macro bodies as a raw `TokenStream`, so the bare `visit_lit`
    /// walker never descends into them — we must walk the token trees ourselves.
    fn visit_macro(&mut self, i: &'ast Macro) {
        let mut macro_hits: Vec<String> = Vec::new();
        for tok in i.tokens.clone().into_iter() {
            collect_str_lits(&tok, &mut macro_hits);
        }
        for val in macro_hits {
            let line = locate_line(&self.current_source, &val);
            self.hits.push((self.current_file.clone(), line, val));
        }
        syn::visit::visit_macro(self, i);
    }
}

/// Recurse through macro token trees, re-parsing `TokenTree::Literal` tokens as
/// `LitStr` and descending into `TokenTree::Group` for nested parens/braces.
fn collect_str_lits(tok: &TokenTree, out: &mut Vec<String>) {
    match tok {
        TokenTree::Literal(lit) => {
            // Re-parse the literal token as a LitStr (silently no-op for non-strings).
            let ts: proc_macro2::TokenStream = TokenTree::Literal(lit.clone()).into();
            if let Ok(ls) = syn::parse2::<syn::LitStr>(ts) {
                let val = ls.value();
                if contains_cjk(&val) {
                    out.push(val);
                }
            }
        }
        TokenTree::Group(g) => {
            for t in g.stream().into_iter() {
                collect_str_lits(&t, out);
            }
        }
        _ => {}
    }
}

/// Best-effort 1-based line lookup of `literal_value` within `source`.
///
/// `proc_macro2::Span` does not expose byte offsets portably outside a real
/// proc-macro context (the `Span::start()` API requires the `proc-macro`
/// feature, which is gated to nightly). We instead scan the source for the
/// literal's *value* text — a literal value is unique enough per file that this
/// is reliable for the CJK-gate's "report what to translate" purpose, and any
/// line ambiguity does not affect the pass/fail verdict.
fn locate_line(source: &str, literal_value: &str) -> usize {
    for (idx, line) in source.lines().enumerate() {
        if line.contains(literal_value) {
            return idx + 1;
        }
    }
    // Fall back to line 1 (the hit is still reported with file + literal value).
    1
}

/// CJK Unicode block ranges (FOUND-04 edge "encoding").
///
/// Covers the four script families named in D-07:
/// - Han (Unified Ideographs + Ext A + Ext B)
/// - Hiragana
/// - Katakana (BMP + Phonetic Extensions)
/// - Hangul (Syllables + Jamo + Compatibility Jamo)
///
/// Emoji (e.g. `⭐`, `🚀`) and Latin are correctly EXCLUDED — confirmed by
/// `src/database/suffix_query.rs` star-emoji literals not flagging. `char` is a
/// 21-bit Unicode scalar value, so supplementary-plane ranges (U+20000+) work
/// without byte arithmetic.
fn contains_cjk(s: &str) -> bool {
    s.chars().any(|c| {
        ('\u{4E00}'..='\u{9FFF}').contains(&c) // CJK Unified Ideographs (Han)
            || ('\u{3400}'..='\u{4DBF}').contains(&c) // CJK Unified Ideographs Extension A
            || ('\u{20000}'..='\u{2A6DF}').contains(&c) // CJK Unified Ideographs Extension B
            || ('\u{3040}'..='\u{309F}').contains(&c) // Hiragana
            || ('\u{30A0}'..='\u{30FF}').contains(&c) // Katakana
            || ('\u{31F0}'..='\u{31FF}').contains(&c) // Katakana Phonetic Extensions
            || ('\u{AC00}'..='\u{D7AF}').contains(&c) // Hangul Syllables
            || ('\u{1100}'..='\u{11FF}').contains(&c) // Hangul Jamo
            || ('\u{3130}'..='\u{318F}').contains(&c) // Hangul Compatibility Jamo
    })
}

/// Returns true if `path` is one of the git-tracked-but-not-compiled dead files
/// in `pyo3/src/` that must be excluded from the CJK scan (RESEARCH.md §1 A1).
fn is_dead_pyo3_file(path: &Path) -> bool {
    let s = path.to_string_lossy();
    s.contains("database_backup")
        || s.contains("database_new_approaches")
        || s.contains("stage1_fix_backup")
}

/// Returns true if `path` is in the exempt `src/cli/` subtree.
fn is_cli_file(path: &Path) -> bool {
    path.to_string_lossy().contains("/cli/")
}

/// Enumerate all in-scope `.rs` source files to scan.
fn enumerate_source_files() -> Vec<PathBuf> {
    let mut out = Vec::new();
    let cwd = std::env::var("CARGO_MANIFEST_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| std::env::current_dir().expect("cwd"));

    // Repo root = parent of the rustkmer crate (this Cargo.toml lives at <root>/Cargo.toml).
    let repo_root = cwd.as_path();

    // src/**/*.rs excluding src/cli/**
    let src_dir = repo_root.join("src");
    if src_dir.is_dir() {
        for entry in WalkDir::new(&src_dir).into_iter().filter_map(Result::ok) {
            let p = entry.path();
            if p.extension().and_then(|e| e.to_str()) == Some("rs") && !is_cli_file(p) {
                out.push(p.to_path_buf());
            }
        }
    }

    // pyo3/src/**/*.rs excluding dead files
    let pyo3_dir = repo_root.join("pyo3").join("src");
    if pyo3_dir.is_dir() {
        for entry in WalkDir::new(&pyo3_dir).into_iter().filter_map(Result::ok) {
            let p = entry.path();
            if p.extension().and_then(|e| e.to_str()) == Some("rs") && !is_dead_pyo3_file(p) {
                out.push(p.to_path_buf());
            }
        }
    }

    out.sort();
    out
}

#[test]
fn no_cjk_string_literals_in_scope() {
    let files = enumerate_source_files();
    assert!(
        !files.is_empty(),
        "source enumeration found no files (cwd wrong?)"
    );

    let mut all_hits: Vec<Hit> = Vec::new();
    for file in &files {
        let source = match std::fs::read_to_string(file) {
            Ok(s) => s,
            Err(e) => panic!("failed to read {}: {}", file.display(), e),
        };
        let syn_file = match syn::parse_file(&source) {
            Ok(f) => f,
            Err(e) => panic!("failed to parse {}: {}", file.display(), e),
        };
        let mut scanner = CjkLiteralScanner {
            current_file: file.clone(),
            current_source: source,
            hits: Vec::new(),
            in_doc_attr_stack: Vec::new(),
        };
        scanner.visit_file(&syn_file);
        all_hits.extend(scanner.hits);
    }

    if !all_hits.is_empty() {
        let mut msg = String::new();
        msg.push_str(&format!(
            "\nFOUND-04 violation: {} CJK string literal(s) found in scope.\n",
            all_hits.len()
        ));
        msg.push_str("Translate (do NOT delete) each to English. Offending literals:\n\n");
        for (path, line, lit) in &all_hits {
            msg.push_str(&format!("  {}:{}: {:?}\n", path.display(), line, lit));
        }
        msg.push_str("\nSee RESEARCH.md §1 + SPEC edge R4/encoding for the block ranges.\n");
        panic!("{msg}");
    }
}

#[test]
fn contains_cjk_detects_each_block() {
    // Sanity: each named block must trip the detector on at least one representative char.
    assert!(contains_cjk("字")); // Han U+4E00-9FFF
    assert!(contains_cjk("㐀")); // Han Ext A U+3400-4DBF
    assert!(contains_cjk("𠀀")); // Han Ext B U+20000-2A6DF
    assert!(contains_cjk("ひ")); // Hiragana U+3040-309F
    assert!(contains_cjk("カ")); // Katakana U+30A0-30FF
    assert!(contains_cjk("ㄱ")); // Hangul Compat Jamo U+3130-318F (U+3131)
    assert!(contains_cjk("가")); // Hangul Syllables U+AC00-D7AF
    assert!(contains_cjk("ᄀ")); // Hangul Jamo U+1100-11FF
                                 // Mixed English+CJK must trip (SPEC edge R4/empty: >=1 CJK char fails).
    assert!(contains_cjk("Error: 文件不存在"));
}

#[test]
fn contains_cjk_allows_emoji_and_latin() {
    // SPEC edge R4/encoding: emoji and Latin are out of CJK scope.
    assert!(!contains_cjk("⭐ star"));
    assert!(!contains_cjk("🚀 rocket"));
    assert!(!contains_cjk("plain ASCII english"));
    assert!(!contains_cjk("with accents éñü"));
}

#[test]
fn dead_file_exclusion_patterns_match() {
    // RESEARCH.md §1 A1: the dead files must be filtered out.
    assert!(is_dead_pyo3_file(Path::new("pyo3/src/database_backup.rs")));
    assert!(is_dead_pyo3_file(Path::new(
        "pyo3/src/database_new_approaches.rs"
    )));
    assert!(is_dead_pyo3_file(Path::new(
        "pyo3/src/something.stage1_fix_backup"
    )));
    // Live files must NOT be excluded.
    assert!(!is_dead_pyo3_file(Path::new("pyo3/src/database.rs")));
    assert!(!is_dead_pyo3_file(Path::new("pyo3/src/counter.rs")));
}

#[test]
fn cli_files_are_excluded_from_scan() {
    // src/cli/** is the FOUND-04 boundary exemption.
    assert!(is_cli_file(Path::new("src/cli/commands/count.rs")));
    assert!(is_cli_file(Path::new("src/cli/args.rs")));
    assert!(!is_cli_file(Path::new("src/lib.rs")));
    assert!(!is_cli_file(Path::new("src/database/format.rs")));
}
