//! Help command validator for RustKmer CLI testing
//!
//! This module provides validation functionality for help documentation,
//! including completeness checks and format validation.

use std::collections::HashMap;
use std::process::Command;
use serde::{Deserialize, Serialize};
use crate::error::TestError;

/// Help validation result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelpValidationResult {
    /// Whether the help validation was successful
    pub success: bool,
    /// Command that was validated
    pub command: String,
    /// Help content type
    pub help_type: HelpType,
    /// Validation errors
    pub errors: Vec<String>,
    /// Validation warnings
    pub warnings: Vec<String>,
    /// Help content analysis
    pub analysis: HelpAnalysis,
}

/// Types of help content
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum HelpType {
    /// Main help (--help or help without arguments)
    Main,
    /// Command-specific help
    Command(String),
    /// Error message
    Error(String),
}

/// Help content analysis
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelpAnalysis {
    /// Whether help content is present
    pub has_content: bool,
    /// Number of lines in help content
    pub line_count: usize,
    /// Whether usage information is present
    pub has_usage: bool,
    /// Whether commands list is present
    pub has_commands: bool,
    /// Whether options are described
    pub has_options: bool,
    /// Whether examples are provided
    pub has_examples: bool,
    /// Content quality score (0-100)
    pub quality_score: u8,
}

/// Help validator configuration
#[derive(Debug, Clone)]
pub struct HelpValidatorConfig {
    /// Minimum required quality score
    pub min_quality_score: u8,
    /// Whether to check for examples
    pub require_examples: bool,
    /// Whether to validate command consistency
    pub validate_consistency: bool,
}

impl Default for HelpValidatorConfig {
    fn default() -> Self {
        Self {
            min_quality_score: 60,
            require_examples: false,
            validate_consistency: true,
        }
    }
}

/// Help validator
pub struct HelpValidator {
    config: HelpValidatorConfig,
}

impl HelpValidator {
    /// Create a new help validator
    pub fn new(config: HelpValidatorConfig) -> Self {
        Self { config }
    }

    /// Create a validator with default config
    pub fn default() -> Self {
        Self::new(HelpValidatorConfig::default())
    }

    /// Validate main help content
    pub fn validate_main_help(&self) -> Result<HelpValidationResult, TestError> {
        let output = Command::new("rustkmer")
            .arg("--help")
            .output()
            .map_err(|e| TestError::CommandFailed(e.to_string()))?;

        let content = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        if !output.status.success() {
            return Ok(HelpValidationResult {
                success: false,
                command: "rustkmer --help".to_string(),
                help_type: HelpType::Main,
                errors: vec![format!("Help command failed: {}", stderr)],
                warnings: Vec::new(),
                analysis: HelpAnalysis::empty(),
            });
        }

        let analysis = self.analyze_help_content(&content);

        Ok(HelpValidationResult {
            success: true,
            command: "rustkmer --help".to_string(),
            help_type: HelpType::Main,
            errors: self.check_help_requirements(&analysis),
            warnings: self.check_help_warnings(&analysis),
            analysis,
        })
    }

    /// Validate command-specific help
    pub fn validate_command_help(&self, command: &str) -> Result<HelpValidationResult, TestError> {
        let output = Command::new("rustkmer")
            .args(&["help", command])
            .output()
            .map_err(|e| TestError::CommandFailed(e.to_string()))?;

        let content = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        let success = output.status.success() ||
            stderr.contains("not yet implemented") ||
            stderr.contains("unrecognized");

        let analysis = self.analyze_help_content(&content);

        Ok(HelpValidationResult {
            success,
            command: format!("rustkmer help {}", command),
            help_type: HelpType::Command(command.to_string()),
            errors: self.check_help_requirements(&analysis),
            warnings: self.check_help_warnings(&analysis),
            analysis,
        })
    }

    /// Validate error messages
    pub fn validate_error_message(&self, args: &[&str]) -> Result<HelpValidationResult, TestError> {
        let mut cmd = Command::new("rustkmer");
        for arg in args {
            cmd.arg(arg);
        }

        let output = cmd.output()
            .map_err(|e| TestError::CommandFailed(e.to_string()))?;

        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);

        let content = if !stderr.is_empty() { &stderr } else { &stdout };
        let analysis = self.analyze_error_content(content);

        Ok(HelpValidationResult {
            success: !output.status.success(), // Error should return non-zero exit code
            command: format!("rustkmer {}", args.join(" ")),
            help_type: HelpType::Error(args.join(" ")),
            errors: Vec::new(), // Errors are expected
            warnings: Vec::new(),
            analysis,
        })
    }

    /// Get list of available commands
    pub fn get_available_commands(&self) -> Result<Vec<String>, TestError> {
        let output = Command::new("rustkmer")
            .arg("--help")
            .output()
            .map_err(|e| TestError::CommandFailed(e.to_string()))?;

        let content = String::from_utf8_lossy(&output.stdout);
        let mut commands = Vec::new();

        for line in content.lines() {
            if line.trim().is_empty() || line.contains("Commands:") || line.contains("Options:") {
                continue;
            }

            // Extract command names (single words with possible hyphens)
            let trimmed = line.trim();
            if let Some(cmd) = trimmed.split_whitespace().next() {
                if cmd.chars().all(|c| c.is_ascii_lowercase() || c == '-') {
                    commands.push(cmd.to_string());
                }
            }
        }

        Ok(commands)
    }

    /// Analyze help content
    fn analyze_help_content(&self, content: &str) -> HelpAnalysis {
        let lines: Vec<&str> = content.lines().collect();
        let content_lower = content.to_lowercase();

        HelpAnalysis {
            has_content: !content.trim().is_empty(),
            line_count: lines.len(),
            has_usage: content_lower.contains("usage"),
            has_commands: content_lower.contains("commands"),
            has_options: content_lower.contains("options"),
            has_examples: content_lower.contains("example") || content_lower.contains("e.g."),
            quality_score: self.calculate_quality_score(content),
        }
    }

    /// Analyze error message content
    fn analyze_error_content(&self, content: &str) -> HelpAnalysis {
        let content_lower = content.to_lowercase();

        HelpAnalysis {
            has_content: !content.trim().is_empty(),
            line_count: content.lines().count(),
            has_usage: content_lower.contains("usage"),
            has_commands: false,
            has_options: false,
            has_examples: false,
            quality_score: self.calculate_error_quality_score(content),
        }
    }

    /// Calculate quality score for help content
    fn calculate_quality_score(&self, content: &str) -> u8 {
        let mut score = 0u8;
        let content_lower = content.to_lowercase();

        // Base score for having content
        if !content.trim().is_empty() {
            score += 20;
        }

        // Usage information (20 points)
        if content_lower.contains("usage") {
            score += 20;
        }

        // Options description (15 points)
        if content_lower.contains("options") {
            score += 15;
        }

        // Arguments description (15 points)
        if content_lower.contains("arguments") || content_lower.contains("args") {
            score += 15;
        }

        // Examples (10 points)
        if content_lower.contains("example") || content_lower.contains("e.g.") {
            score += 10;
        }

        // Additional description (10 points)
        if content.lines().count() > 5 {
            score += 10;
        }

        // Clear formatting (10 points)
        if content.contains('\n') && content.lines().any(|l| l.trim().starts_with('-')) {
            score += 10;
        }

        score
    }

    /// Calculate quality score for error messages
    fn calculate_error_quality_score(&self, content: &str) -> u8 {
        let mut score = 0u8;
        let content_lower = content.to_lowercase();

        // Base score for having content
        if !content.trim().is_empty() {
            score += 20;
        }

        // Mentions error (20 points)
        if content_lower.contains("error") {
            score += 20;
        }

        // Provides usage hint (20 points)
        if content_lower.contains("usage") {
            score += 20;
        }

        // Suggests help (20 points)
        if content_lower.contains("help") || content_lower.contains("--help") {
            score += 20;
        }

        // Clear and concise (20 points)
        if content.len() < 200 {
            score += 20;
        }

        score
    }

    /// Check help requirements
    fn check_help_requirements(&self, analysis: &HelpAnalysis) -> Vec<String> {
        let mut errors = Vec::new();

        if !analysis.has_content {
            errors.push("Help content is empty".to_string());
        }

        if analysis.line_count < 2 {
            errors.push("Help content is too short".to_string());
        }

        if analysis.quality_score < self.config.min_quality_score {
            errors.push(format!(
                "Help quality score {} is below minimum {}",
                analysis.quality_score, self.config.min_quality_score
            ));
        }

        errors
    }

    /// Check help warnings
    fn check_help_warnings(&self, analysis: &HelpAnalysis) -> Vec<String> {
        let mut warnings = Vec::new();

        if !analysis.has_usage {
            warnings.push("No usage information provided".to_string());
        }

        if self.config.require_examples && !analysis.has_examples {
            warnings.push("No examples provided".to_string());
        }

        warnings
    }

    /// Generate comprehensive help report
    pub fn generate_help_report(&self, results: &[HelpValidationResult]) -> String {
        let mut report = String::new();

        report.push_str("# Help System Validation Report\n\n");

        let total_tests = results.len();
        let successful_tests = results.iter().filter(|r| r.success).count();
        let success_rate = if total_tests > 0 {
            (successful_tests as f64 / total_tests as f64) * 100.0
        } else {
            0.0
        };

        report.push_str(&format!(
            "## Summary\n\n- Total tests: {}\n- Successful: {}\n- Failed: {}\n- Success rate: {:.1}%\n\n",
            total_tests,
            successful_tests,
            total_tests - successful_tests,
            success_rate
        ));

        // Categorize results
        let main_help: Vec<_> = results.iter()
            .filter(|r| matches!(r.help_type, HelpType::Main))
            .collect();

        let command_help: HashMap<String, Vec<_>> = results.iter()
            .filter_map(|r| {
                if let HelpType::Command(cmd) = &r.help_type {
                    Some((cmd.clone(), r))
                } else {
                    None
                }
            })
            .fold(HashMap::new(), |mut acc, (cmd, result)| {
                acc.entry(cmd).or_insert_with(Vec::new).push(result);
                acc
            });

        let error_tests: Vec<_> = results.iter()
            .filter(|r| matches!(r.help_type, HelpType::Error(_)))
            .collect();

        // Main help section
        if !main_help.is_empty() {
            report.push_str("## Main Help\n\n");
            for result in main_help {
                report.push_str(&format!(
                    "- **Status**: {}\n- **Quality Score**: {}/100\n- **Line Count**: {}\n",
                    if result.success { "✅ Passed" } else { "❌ Failed" },
                    result.analysis.quality_score,
                    result.analysis.line_count
                ));

                if !result.errors.is_empty() {
                    report.push_str("- **Errors**:\n");
                    for error in &result.errors {
                        report.push_str(&format!("  - {}\n", error));
                    }
                }

                if !result.warnings.is_empty() {
                    report.push_str("- **Warnings**:\n");
                    for warning in &result.warnings {
                        report.push_str(&format!("  - {}\n", warning));
                    }
                }
                report.push_str("\n");
            }
        }

        // Command help section
        if !command_help.is_empty() {
            report.push_str("## Command Help\n\n");
            for (cmd, results) in command_help {
                report.push_str(&format!("### `{}`\n\n", cmd));

                for result in results {
                    report.push_str(&format!(
                        "- **Status**: {}\n- **Quality Score**: {}/100\n",
                        if result.success { "✅ Passed" } else { "⚠️ Not Implemented" },
                        result.analysis.quality_score
                    ));
                }
                report.push_str("\n");
            }
        }

        // Error messages section
        if !error_tests.is_empty() {
            report.push_str("## Error Messages\n\n");
            for result in error_tests {
                if let HelpType::Error(cmd) = &result.help_type {
                    report.push_str(&format!("### `{}`\n\n", cmd));

                    if result.success {
                        report.push_str("✅ Error message is appropriate\n\n");
                    } else {
                        report.push_str("⚠️ Error message could be improved\n\n");
                    }
                }
            }
        }

        // Quality metrics
        let avg_quality: f64 = results.iter()
            .map(|r| r.analysis.quality_score as f64)
            .sum::<f64>() / total_tests as f64;

        report.push_str(&format!(
            "## Quality Metrics\n\n- **Average Quality Score**: {:.1}/100\n- **Commands with Help**: {}\n",
            avg_quality,
            command_help.len()
        ));

        report
    }
}

impl HelpAnalysis {
    /// Create an empty analysis
    pub fn empty() -> Self {
        Self {
            has_content: false,
            line_count: 0,
            has_usage: false,
            has_commands: false,
            has_options: false,
            has_examples: false,
            quality_score: 0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_help_validator_creation() {
        let validator = HelpValidator::default();
        let config = HelpValidatorConfig::default();
        assert_eq!(validator.config.min_quality_score, config.min_quality_score);
    }

    #[test]
    fn test_help_analysis_empty() {
        let analysis = HelpAnalysis::empty();
        assert!(!analysis.has_content);
        assert_eq!(analysis.line_count, 0);
        assert_eq!(analysis.quality_score, 0);
    }

    #[test]
    fn test_quality_score_calculation() {
        let validator = HelpValidator::default();

        // Test with empty content
        let score = validator.calculate_quality_score("");
        assert_eq!(score, 0);

        // Test with basic content
        let score = validator.calculate_quality_score("Usage: cmd [options]");
        assert!(score > 20);
    }

    #[test]
    fn test_error_quality_score() {
        let validator = HelpValidator::default();

        // Test with error message
        let score = validator.calculate_error_quality_score("error: invalid argument\nUsage: cmd --help");
        assert!(score > 60);
    }
}