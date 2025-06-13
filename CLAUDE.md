# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing and Linting
- `ruff check` - Run linting checks
- `ruff format` - Format code
- `pytest` - Run tests (if any exist in tests/ directory)

### Package Management
- `uv sync` - Install dependencies
- `uv run plainr` - Run the CLI tool directly

### Installation and Testing
- `uv build` - Build the package
- `plainr --help` - Show CLI help after installation

## Project Overview

**Plainr** is a comprehensive CLI tool for managing Plain License implementations and providing plain language linting for developers. The project aims to be "Understanding as DevOps" - making readability and plain language a core part of development workflows.

### Planned Feature Set (from main.py help)

- **`plainr compare`** - Compare readability of Plain License licenses with original counterparts (✅ implemented)
- **`plainr about`** - Get information about readability metrics (✅ implemented) 
- **`plainr score`** - Calculate readability scores for any text (🚧 planned)
- **`plainr init`** - Add a Plain License to your project (🚧 planned)
- **`plainr update`** - Update your Plain License to latest version (🚧 planned)
- **`plainr action`** - Add GitHub Action for readability auditing and license updates (🚧 planned)

### Architecture Overview

The current implementation focuses on readability comparison functionality, with extensive type safety and Rich-based output formatting. The architecture is designed to accommodate the planned expansion into license management and CI/CD integration.

### Core Components

- **Main CLI** (`src/plainr/main.py`): Entry point using cyclopts App with subcommands
- **Commands** (`src/plainr/commands/`): Individual command implementations
- **Types** (`src/plainr/types/`): Comprehensive type definitions with heavy annotation to compensate for py-readability-metrics' lack of type hints
- **License Handling** (`src/plainr/_licenses/`): License content management and parsing infrastructure
- **Console** (`src/plainr/_console/`): Rich-based console interface with CI detection
- **Configuration** (`src/plainr/config/`): Runtime constants and environment detection

### Key Architecture Decisions

- **Type Safety First**: Extensive TypedDict, NamedTuple, and type annotations throughout to fill gaps in py-readability-metrics
- **Readability Library Migration**: Current code uses py-readability-metrics but is structured to migrate to "Readable" (a modernized fork) when ready
- **Rich Integration**: Console output optimized for both interactive use and CI environments
- **Extensible Command Pattern**: CLI structure designed for easy addition of planned features

### Dependencies

- `cyclopts` - Modern CLI framework
- `py-readability-metrics` - Current readability calculations (to be replaced by "Readable")
- `rich` - Enhanced console output and formatting
- `nltk` - Natural language processing data
- `ez-yaml` - YAML processing

### Future Migration Notes

- Many types in `src/plainr/types/readability.py` exist to provide type safety for py-readability-metrics
- When migrating to "Readable" library, much of the readability handling will be externalized
- License management features will expand the `_licenses/` and related infrastructure significantly