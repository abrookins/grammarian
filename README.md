# Grammarian

A "Drake Equation" for English writing quality — a CLI tool that produces a single quality score from multiple prose metrics.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](https://github.com)

## Overview

Grammarian produces a single **Writing Quality Index (WQI)** score (0.0-1.0) by combining multiple prose quality metrics using a geometric mean, similar to how [MFCQI](https://github.com/bsbodden/mfcqi) works for code quality.

**Key Features:**
- Single composite score from multiple metrics
- Git integration for analyzing only changed files
- Configurable profiles for different writing styles
- Optional AI-powered feedback via LiteLLM
- CI/CD friendly with JSON output and exit codes
- Rich terminal output with detailed issue reporting

## Installation

```bash
# Using pip
pip install grammarian

# Using uv (recommended)
uv pip install grammarian

# From source
git clone https://github.com/youruser/grammarian.git
cd grammarian
uv pip install -e .
```

### Optional Dependencies

For AI-powered feedback:
```bash
pip install grammarian[ai]
# or
pip install litellm
```

For enhanced grammar checking with LanguageTool:
```bash
pip install language-tool-python
```

## Quick Start

```bash
# Analyze a single file
grammarian analyze README.md

# Analyze multiple files or directories
grammarian analyze README.md docs/ CONTRIBUTING.md

# Analyze only changed files (git diff)
grammarian analyze --diff

# Analyze staged changes only
grammarian analyze --diff --staged

# Use a specific writing profile
grammarian analyze docs/ --profile technical

# Get AI-powered feedback
grammarian analyze README.md --ai

# JSON output for CI/CD
grammarian analyze . --format json

# Fail if score is below threshold
grammarian analyze . --min-score 0.75
```

## The Writing Quality Index (WQI)

The WQI is calculated using a **geometric mean** of individual metric scores:

```
WQI = (M₁ × M₂ × M₃ × M₄)^(1/4)
```

This approach ensures that:
- A low score in any single metric significantly impacts the overall score
- Balanced quality across all dimensions is rewarded
- The score ranges from 0.0 (poor) to 1.0 (excellent)

### Score Interpretation

| Score Range | Rating | Description |
|-------------|--------|-------------|
| 0.90 - 1.00 | Excellent | Publication-ready prose |
| 0.75 - 0.89 | Good | Minor improvements possible |
| 0.60 - 0.74 | Fair | Several areas need attention |
| 0.40 - 0.59 | Poor | Significant revision needed |
| 0.00 - 0.39 | Very Poor | Major rewrite recommended |

## Metrics

Grammarian evaluates text across four dimensions:

### Readability

Measures how easy the text is to read using established formulas:

- **Flesch-Kincaid Grade Level**: Target grade level for comprehension
- **Gunning Fog Index**: Years of education needed
- **SMOG Index**: Simple Measure of Gobbledygook
- **Coleman-Liau Index**: Character-based readability
- **Automated Readability Index**: Sentence and word length analysis

The metric compares the consensus grade level against a configurable target (default: grade 10).

### Grammar

Checks for grammatical errors and issues:

- **LanguageTool** (if installed): Comprehensive grammar, punctuation, and style checking
- **Proselint** (fallback): Prose linting for common writing issues

Issues are weighted by severity to calculate the score.

### Spelling

Identifies spelling errors with smart filtering:

- Recognizes common technical terms (API, JSON, HTTP, etc.)
- Ignores code blocks (fenced with ```)
- Supports custom word lists
- Provides correction suggestions

### Style

Analyzes writing style and clarity:

- **Passive Voice Detection**: Identifies passive constructions
- **Sentence Length**: Flags sentences exceeding the configured maximum
- **Weasel Words**: Detects vague qualifiers (very, really, quite, etc.)

## Configuration

Grammarian looks for configuration in these locations (in order):

1. `.grammarian.toml` in current or parent directories
2. `grammarian.toml` in current or parent directories
3. `pyproject.toml` under `[tool.grammarian]`

### Generating a Configuration File

Use the `config init` command to generate a comprehensive example configuration:

```bash
# Generate .grammarian.toml in current directory
grammarian config init

# Generate with a custom filename
grammarian config init --output custom.toml

# Preview the config without writing to file
grammarian config init --stdout

# Overwrite an existing config file
grammarian config init --force
```

The generated file includes all available options with documentation comments.

### Configuration File Format

```toml
# .grammarian.toml

# Default profile to use
default_profile = "technical"

# File extensions to analyze
extensions = [".md", ".txt", ".rst"]

# Profile definitions
[profiles.technical]
name = "technical"
description = "Technical documentation"
target_grade = 12
max_sentence_words = 35
check_passive = false  # Technical docs often use passive voice
check_weasel = true
custom_words = ["kubernetes", "microservice", "async"]

[profiles.casual]
name = "casual"
description = "Blog posts and casual writing"
target_grade = 8
max_sentence_words = 25
check_passive = true
check_weasel = true

[profiles.academic]
name = "academic"
description = "Academic and formal writing"
target_grade = 14
max_sentence_words = 40
check_passive = true
check_weasel = false

# Metric-specific configuration
[metrics.readability]
enabled = true
weight = 1.0

[metrics.grammar]
enabled = true
weight = 1.5  # Weight grammar more heavily
options = { disabled_rules = ["WHITESPACE_RULE"] }

[metrics.spelling]
enabled = true
weight = 1.0
options = { custom_words = ["grammarian", "WQI"] }

[metrics.style]
enabled = true
weight = 1.0

# LLM configuration for AI feedback
[llm]
enabled = false
provider = "openai"
model = "gpt-4o-mini"
temperature = 0.3
context = "Technical documentation for developers"
```

### Built-in Profiles

| Profile | Target Grade | Max Sentence | Passive Check | Use Case |
|---------|--------------|--------------|---------------|----------|
| `default` | 10 | 30 words | Yes | General writing |
| `technical` | 12 | 35 words | No | Technical docs |
| `casual` | 8 | 25 words | Yes | Blog posts |
| `academic` | 14 | 40 words | Yes | Academic papers |

### Disabling Specific Rules

You can disable specific grammar and style rules that don't apply to your project. Add them to the `disabled_rules` list in your grammar metric configuration:

```toml
[metrics.grammar.options]
disabled_rules = [
    "typography.symbols.curly_quotes",  # Disable curly quote suggestions
    "typography.symbols.ellipsis",      # Disable ellipsis suggestions
    "misc.phrasal_adjectives",          # Hyphenation suggestions
]
```

**Common Proselint rules to disable:**

| Rule ID | Description |
|---------|-------------|
| `typography.symbols.curly_quotes` | Suggests using curly quotes instead of straight quotes |
| `typography.symbols.ellipsis` | Suggests using the ellipsis character (…) |
| `typography.symbols.sentence_spacing` | Checks spacing after periods |
| `misc.phrasal_adjectives` | Hyphenation of phrasal adjectives |
| `misc.preferred_forms` | Suggests preferred word forms |
| `leonard.exclamation` | Warns about exclamation marks |
| `redundancy.ras_syndrome` | Redundant acronym syndrome (e.g., "ATM machine") |
| `dates_times.am_pm` | AM/PM formatting suggestions |

**LanguageTool rules** (if installed):

| Rule ID | Description |
|---------|-------------|
| `WHITESPACE_RULE` | Whitespace issues |
| `EN_QUOTES` | Quote style checking |
| `COMMA_PARENTHESIS_WHITESPACE` | Comma/parenthesis spacing |
| `UPPERCASE_SENTENCE_START` | Sentence capitalization |

Run `grammarian config init` to generate a configuration file with all common rules documented.

## Git Integration

Grammarian integrates with Git to analyze only changed content:

```bash
# Analyze all unstaged changes
grammarian analyze --diff

# Analyze only staged changes (useful for pre-commit)
grammarian analyze --diff --staged
```

This is particularly useful for:
- Pre-commit hooks
- CI/CD pipelines
- Incremental documentation review

## AI-Powered Feedback

With LiteLLM installed, Grammarian can provide AI-powered writing suggestions:

```bash
# Get AI feedback on your writing
grammarian analyze README.md --ai

# Use a specific model
grammarian analyze README.md --ai --ai-model gpt-4
```

The AI advisor:
- Analyzes the WQI results and identified issues
- Provides context-aware suggestions
- Offers specific rewrite recommendations
- Considers your configured writing context

### Supported LLM Providers

Grammarian uses [LiteLLM](https://github.com/BerriAI/litellm), supporting 100+ LLM providers:

- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)
- Azure OpenAI
- Local models via Ollama
- And many more

Set your API key via environment variable:
```bash
export OPENAI_API_KEY="your-key"
# or
export ANTHROPIC_API_KEY="your-key"
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Writing Quality Check

on: [push, pull_request]

jobs:
  grammarian:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Grammarian
        run: pip install grammarian

      - name: Check writing quality
        run: grammarian analyze docs/ --min-score 0.7 --format json
```

### Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: grammarian
        name: Check writing quality
        entry: grammarian analyze --diff --staged --min-score 0.7
        language: python
        types: [markdown, text, rst]
        pass_filenames: false
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (score meets threshold) |
| 1 | Score below `--min-score` threshold |
| 2 | Error (invalid input, missing files) |

## CLI Reference

```
grammarian [OPTIONS] COMMAND [ARGS]...

Commands:
  analyze  Analyze text files for writing quality
  config   Manage Grammarian configuration

Options:
  --version  Show version and exit
  --help     Show help message and exit
```

### `analyze` Command

```
grammarian analyze [OPTIONS] [PATHS]...

Arguments:
  PATHS  Files or directories to analyze

Options:
  --min-score FLOAT        Minimum WQI score (exit 1 if below)
  --format [rich|json]     Output format (default: rich)
  --diff                   Analyze only changed files (git diff)
  --staged                 With --diff, analyze only staged changes
  --profile TEXT           Writing profile to use
  --ai                     Enable AI-powered feedback
  --ai-model TEXT          LLM model for AI feedback
  --help                   Show help message and exit
```

### `config` Command

```
grammarian config [OPTIONS] COMMAND [ARGS]...

Commands:
  init  Generate an example configuration file
```

### `config init` Command

```
grammarian config init [OPTIONS]

Options:
  -o, --output PATH  Output file path (default: .grammarian.toml)
  -s, --stdout       Print to stdout instead of writing to file
  -f, --force        Overwrite existing configuration file
  --help             Show help message and exit
```

## Programmatic Usage

```python
from grammarian.calculator import Calculator
from grammarian.metrics.readability import ReadabilityMetric
from grammarian.metrics.grammar import GrammarMetric
from grammarian.metrics.spelling import SpellingMetric
from grammarian.metrics.style import StyleMetric

# Create calculator with metrics
calculator = Calculator([
    ReadabilityMetric({"target_grade": 10}),
    GrammarMetric(),
    SpellingMetric({"custom_words": ["API", "JSON"]}),
    StyleMetric({"check_passive": True, "max_sentence_words": 30}),
])

# Analyze text
text = """
Your document content here.
"""

result = calculator.analyze(text)

print(f"WQI Score: {result.wqi_score:.2f}")
print(f"Rating: {result.rating.value}")

for metric in result.metrics:
    print(f"  {metric.name}: {metric.score:.2f}")
    for issue in metric.issues[:3]:
        print(f"    - {issue.message}")
```

## Development

```bash
# Clone the repository
git clone https://github.com/youruser/grammarian.git
cd grammarian

# Create virtual environment
uv venv
source .venv/bin/activate

# Install in development mode
uv pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=grammarian --cov-report=term-missing

# Run the CLI
grammarian analyze README.md
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure all tests pass (`pytest tests/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Acknowledgments

- Inspired by [MFCQI](https://github.com/bsbodden/mfcqi) for code quality
- Built with [Click](https://click.palletsprojects.com/), [Rich](https://rich.readthedocs.io/), and [Pydantic](https://docs.pydantic.dev/)
- Readability metrics via [textstat](https://github.com/shivam5992/textstat)
- Grammar checking via [proselint](https://github.com/amperser/proselint) and [LanguageTool](https://languagetool.org/)
- Spell checking via [pyspellchecker](https://github.com/barrust/pyspellchecker)
- LLM integration via [LiteLLM](https://github.com/BerriAI/litellm)


