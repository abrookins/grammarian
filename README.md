# Grammarian

A "Drake Equation" for English writing quality — CLI tool for prose analysis.

## Overview

Grammarian produces a single **Writing Quality Index (WQI)** score (0.0-1.0) by combining multiple prose quality metrics, similar to how [MFCQI](https://github.com/bsbodden/mfcqi) works for code quality.

## Installation

```bash
pip install grammarian
```

## Quick Start

```bash
# Analyze files
grammarian analyze README.md docs/

# Analyze with minimum score threshold (for CI)
grammarian analyze . --min-score 0.75

# JSON output
grammarian analyze . --format json
```

## Metrics

- **Readability**: Flesch-Kincaid, Gunning Fog, SMOG, etc.
- **Grammar**: Grammar and punctuation checking
- **Spelling**: Spell checking
- **Style**: Passive voice, sentence length, clarity
- **Structure**: Paragraph organization

## Configuration

Create a `.grammarian.toml` file:

```toml
[profile]
audience = "software developers"
target_grade = 10

[metrics]
enabled = ["readability", "grammar", "spelling"]
```

## License

MIT


