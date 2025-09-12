# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- GitHub Actions CI/CD workflow for automated testing and deployment
- Dockerfile for containerizing the application
- docker-compose.yml for local development with monitoring stack
- Comprehensive documentation for CI/CD and deployment
- Automated release process with semantic versioning
- Code coverage reporting with Codecov
- Health check endpoint at `/health`
- Interactive API documentation at `/docs` and `/redoc`
- Structured JSON logging for all application logs
- Test infrastructure with unit, integration, and e2e test directories
- Comprehensive logging tests

### Changed

- Moved all test files from repo root to dedicated tests directory
- Updated project structure for better organization
- Improved error handling and logging
- Updated dependencies to latest versions
- Enhanced documentation with deployment instructions
- Optimized Docker image for production use

### Fixed

- Fixed import errors in test files
- Addressed linting issues in the codebase
- Resolved dependency conflicts
- Fixed test assertions to match actual implementation
- JSON parsing errors in client logs by ensuring all logs are properly formatted
- Deprecation warnings for datetime.utcnow()

## [0.1.0] - 2025-09-11 - Initial Release

### Features

- Initial project setup
- Basic Docker MCP server implementation
- Container management tools
