# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased] - 2026-06-01

### Added
- **DeepAgents Patching**: Created `da_patch.py` to handle runtime monkey-patching of the `deepagents` framework without modifying source files addressing an issue with agents using the wrong virtual filepath.
- **UI Settings**: Wired `checkBoxCompressContext` and `spinBoxCompressContextCount` widgets in `settings_dialog.py` to save/load settings to/from `config.json`.

### Changed
- **Context Compression**: Updated the context compressor hook in `mainwindow_app.py` to respect dynamic config values (`enable_context_compression` and `context_compress_threshold`) instead of using hardcoded settings.
- **DeepAgents Integration**: `main.py` and `repl.py` now invoke `da_patch.apply_deepagents_patches()` upon startup. Removed the previous manual edits to `site-packages/deepagents/backends/filesystem.py` to keep the environment clean.

### Fixed
- **Path Duplication**: Fixed an issue where DeepAgents would hallucinate and duplicate virtual paths when given an absolute path by applying an in-memory monkey patch to `FilesystemBackend._resolve_path`.
- **Tracing**: Resolved an issue in `repl.py` where Arize Phoenix tracing would start incorrectly when running config-only arguments (`--config` or `--test-config`).
- **UI Mismatch**: Resolved an `AttributeError` in `settings_dialog.py` by correcting the reference from the removed `txt_emb_model` widget to the new `comboBox`.
