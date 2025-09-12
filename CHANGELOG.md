# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Structured JSON logging for all application logs
- Test infrastructure with unit, integration, and e2e test directories
- Comprehensive logging tests

### Changed

- Moved all test files from repo root to dedicated tests directory
- Updated logging configuration to ensure consistent JSON output
- Improved error handling in logging formatter

### Fixed

- JSON parsing errors in client logs by ensuring all logs are properly formatted
- Deprecation warnings for datetime.utcnow()

## [0.1.0] - 2025-09-11 - Initial Release

### Added

- Initial project setup
- Basic Docker MCP server implementation
- Container management tools
