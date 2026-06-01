# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased] - 2026-06-01

### Added
- **UI Settings**: Wired `checkBoxCompressContext` and `spinBoxCompressContextCount` widgets in `settings_dialog.py` to save/load settings to/from `config.json`.

### Changed
- **Context Compression**: Updated the context compressor hook in `mainwindow_app.py` to respect dynamic config values (`enable_context_compression` and `context_compress_threshold`) instead of using hardcoded settings.

### Fixed
- **Tracing**: Resolved an issue in `repl.py` where Arize Phoenix tracing would start incorrectly when running config-only arguments (`--config` or `--test-config`).
- **UI Mismatch**: Resolved an `AttributeError` in `settings_dialog.py` by correcting the reference from the removed `txt_emb_model` widget to the new `comboBox`.
