"""Main CLI entry point for Redpen."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from redpen import __version__
from redpen.calculator import Calculator
from redpen.core.models import AnalysisResult, Rating

console = Console()


def get_rating_emoji(rating: Rating) -> str:
    """Get emoji for rating."""
    return {
        Rating.EXCELLENT: "⭐",
        Rating.GOOD: "✅",
        Rating.FAIR: "⚠️",
        Rating.POOR: "❌",
    }[rating]


def display_results(result: AnalysisResult) -> None:
    """Display analysis results with rich formatting."""
    # Build metrics table
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Metric", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Rating")

    for metric in result.metrics:
        emoji = get_rating_emoji(metric.rating)
        details = ""
        if metric.details:
            if "consensus_grade" in metric.details:
                details = f" (Grade {metric.details['consensus_grade']})"
        table.add_row(
            metric.name,
            f"{metric.score:.2f}",
            f"{emoji} {metric.rating.value.capitalize()}{details}",
        )

    # Print header
    rating_color = "green" if result.rating == Rating.EXCELLENT else "yellow"
    console.print()
    console.print(
        Panel.fit(
            f"⭐ [bold]Writing Quality Index: {result.wqi_score:.3f}[/bold]",
            title="✨ Redpen Analysis Results",
            border_style=rating_color,
        )
    )
    console.print()
    console.print("[bold]📊 Metrics Breakdown:[/bold]")
    console.print(table)

    # Issues summary
    issues = result.all_issues
    if issues:
        console.print()
        console.print(f"[bold]🔍 Issues Found:[/bold] {len(issues)}")
        for issue in issues[:5]:
            loc = f":{issue.line}" if issue.line else ""
            file_info = f"{issue.file_path}{loc}" if issue.file_path else ""
            prefix = f"{file_info} - " if file_info else ""
            console.print(f"  • {prefix}{issue.message}")
        if len(issues) > 5:
            console.print(f"  ... and {len(issues) - 5} more")

    console.print()



@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """Redpen: A Drake Equation for English writing quality."""
    pass


@cli.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("--min-score", type=float, default=None, help="Minimum WQI score (fails if below)")
@click.option("--format", "output_format", type=click.Choice(["rich", "json"]), default="rich")
@click.option("--diff", "use_diff", is_flag=True, help="Analyze only changed files (git diff)")
@click.option("--staged", is_flag=True, help="Analyze only staged changes (use with --diff)")
@click.option("--profile", "profile_name", default=None, help="Writing style profile (default, technical, casual, academic)")
@click.option("--config", "config_path", type=click.Path(exists=True), default=None, help="Path to config file")
@click.option("--ai", "use_ai", is_flag=True, help="Get AI-powered feedback (requires LLM API key)")
@click.option("--model", "ai_model", default="gpt-4o-mini", help="LLM model for AI feedback")
def analyze(
    paths: tuple[str, ...],
    min_score: float | None,
    output_format: str,
    use_diff: bool,
    staged: bool,
    profile_name: str | None,
    config_path: str | None,
    use_ai: bool,
    ai_model: str,
) -> None:
    """Analyze text files for writing quality."""
    if not paths and not use_diff:
        console.print("[yellow]No paths specified. Use --help for usage or --diff for git changes.[/yellow]")
        return

    # Import and load config
    from redpen.config import RedpenConfig, DEFAULT_PROFILES
    from redpen.metrics.grammar import GrammarMetric
    from redpen.metrics.readability import ReadabilityMetric
    from redpen.metrics.spelling import SpellingMetric
    from redpen.metrics.style import StyleMetric

    # Load configuration
    config = RedpenConfig.load(Path(config_path) if config_path else None)

    # Get profile (from args, config, or default)
    if profile_name and profile_name in DEFAULT_PROFILES:
        profile = DEFAULT_PROFILES[profile_name]
    else:
        profile = config.get_profile(profile_name)

    # Configure metrics based on profile
    calculator = Calculator()
    calculator.add_metric(ReadabilityMetric({"target_grade": profile.target_grade}))
    calculator.add_metric(GrammarMetric())
    calculator.add_metric(SpellingMetric({"custom_words": profile.custom_words}))
    calculator.add_metric(StyleMetric({
        "max_sentence_words": profile.max_sentence_words,
        "check_passive": profile.check_passive,
        "check_weasel": profile.check_weasel,
    }))

    all_text = []
    analyzed_paths: list[Path] = []

    # Handle --diff mode
    if use_diff:
        from redpen.git import get_changed_files

        changed = get_changed_files(staged=staged, extensions=[".md", ".txt", ".rst"])
        if not changed:
            console.print("[yellow]No changed files found.[/yellow]")
            return
        for file_path in changed:
            try:
                all_text.append(file_path.read_text())
                analyzed_paths.append(file_path)
            except Exception as e:
                console.print(f"[red]Error reading {file_path}: {e}[/red]")
    else:
        for path_str in paths:
            path = Path(path_str)
            if path.is_file():
                try:
                    all_text.append(path.read_text())
                    analyzed_paths.append(path)
                except Exception as e:
                    console.print(f"[red]Error reading {path}: {e}[/red]")
            elif path.is_dir():
                for file in path.rglob("*.md"):
                    try:
                        all_text.append(file.read_text())
                        analyzed_paths.append(file)
                    except Exception as e:
                        console.print(f"[red]Error reading {file}: {e}[/red]")

    if not all_text:
        console.print("[yellow]No text files found.[/yellow]")
        return

    combined_text = "\n\n".join(all_text)
    file_display = str(analyzed_paths[0]) if analyzed_paths else "stdin"
    result = calculator.analyze(combined_text, file_path=file_display)
    result.files_analyzed = len(all_text)

    if output_format == "json":
        console.print(result.model_dump_json(indent=2))
    else:
        display_results(result)

    # AI feedback if requested
    if use_ai:
        from redpen.llm import WritingAdvisor

        console.print("[bold]🤖 AI Feedback:[/bold]")
        try:
            advisor = WritingAdvisor(model=ai_model, context=profile.description)
            feedback = advisor.get_feedback(combined_text, result)
            console.print(Panel(feedback, title="Writing Coach", border_style="blue"))
        except ImportError as e:
            console.print(f"[red]LLM not available: {e}[/red]")
        except Exception as e:
            console.print(f"[red]AI feedback failed: {e}[/red]")

    if min_score is not None and result.wqi_score < min_score:
        raise SystemExit(1)


@cli.group()
def config() -> None:
    """Manage Redpen configuration."""
    pass


EXAMPLE_CONFIG = '''\
# Redpen Configuration File
# Generated by: redpen config init
#
# Place this file as .redpen.toml in your project root
# or in any parent directory.

# Default profile to use when --profile is not specified
default_profile = "default"

# File extensions to analyze (when scanning directories)
extensions = [".md", ".txt", ".rst"]

# ============================================================================
# PROFILES
# ============================================================================
# Profiles define writing style settings. You can create custom profiles
# or override the built-in ones: default, technical, casual, academic

[profiles.default]
name = "default"
description = "Balanced settings for general writing"
target_grade = 10              # Target reading grade level (1-20)
max_sentence_words = 30        # Flag sentences longer than this
check_passive = true           # Check for passive voice
check_weasel = true            # Check for weasel words (very, really, etc.)
custom_words = []              # Words to ignore in spell checking

[profiles.technical]
name = "technical"
description = "Technical documentation style"
target_grade = 12
max_sentence_words = 35
check_passive = false          # Passive voice is acceptable in technical docs
check_weasel = true
custom_words = [
    "API", "JSON", "HTTP", "HTTPS", "CLI", "SDK",
    "kubernetes", "microservice", "async", "middleware"
]

[profiles.casual]
name = "casual"
description = "Blog posts and casual writing"
target_grade = 8
max_sentence_words = 25
check_passive = true
check_weasel = false           # More relaxed about qualifiers

[profiles.academic]
name = "academic"
description = "Academic and formal writing"
target_grade = 14
max_sentence_words = 40
check_passive = true
check_weasel = true

# ============================================================================
# METRICS CONFIGURATION
# ============================================================================
# Configure individual metrics: enable/disable, set weight, and options

[metrics.readability]
enabled = true
weight = 1.0                   # Weight in WQI calculation (default: 1.0)
# options = { target_grade = 10 }  # Uncomment to override profile target_grade

[metrics.grammar]
enabled = true
weight = 1.0

[metrics.grammar.options]
# Disable specific grammar/style rules
# For proselint rules, use the check_path like "typography.symbols.curly_quotes"
# For LanguageTool rules, use the rule ID like "WHITESPACE_RULE"
disabled_rules = [
    # "typography.symbols.curly_quotes",  # Disable curly quote suggestions
    # "typography.symbols.ellipsis",      # Disable ellipsis suggestions
    # "typography.symbols.sentence_spacing",  # Disable sentence spacing checks
    # "WHITESPACE_RULE",                  # LanguageTool: whitespace issues
    # "EN_QUOTES",                        # LanguageTool: quote style
]

[metrics.spelling]
enabled = true
weight = 1.0

[metrics.spelling.options]
# Additional words to ignore in spell checking (beyond profile custom_words)
custom_words = [
    "redpen", "WQI"
]

[metrics.style]
enabled = true
weight = 1.0
# options = { check_passive = true, check_weasel = true, max_sentence_words = 30 }

# ============================================================================
# LLM CONFIGURATION (Optional)
# ============================================================================
# Enable AI-powered writing feedback using LiteLLM

[llm]
enabled = false                # Set to true to enable AI feedback
provider = "openai"            # LLM provider (openai, anthropic, etc.)
model = "gpt-4o-mini"          # Model to use
temperature = 0.3              # Lower = more focused, higher = more creative

# Context about your writing to help the LLM provide better feedback
context = """
Technical documentation for software developers.
Focus on clarity and accuracy over stylistic flourishes.
"""

# ============================================================================
# COMMON PROSELINT RULES TO DISABLE
# ============================================================================
# Reference: These are common proselint check_paths you might want to disable
# Add them to metrics.grammar.options.disabled_rules
#
# typography.symbols.curly_quotes      - Suggests using curly quotes
# typography.symbols.ellipsis          - Suggests using ellipsis character
# typography.symbols.sentence_spacing  - Checks spacing after periods
# misc.phrasal_adjectives              - Hyphenation of phrasal adjectives
# misc.preferred_forms                 - Suggests preferred word forms
# leonard.exclamation                  - Warns about exclamation marks
# redundancy.ras_syndrome              - Redundant acronym syndrome
# dates_times.am_pm                    - AM/PM formatting
'''


@config.command("init")
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=".redpen.toml",
    help="Output file path (default: .redpen.toml)",
)
@click.option(
    "--stdout", "-s",
    is_flag=True,
    help="Print to stdout instead of writing to file",
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Overwrite existing configuration file",
)
def config_init(output: str, stdout: bool, force: bool) -> None:
    """Generate an example configuration file.

    Creates a comprehensive .redpen.toml with all available options
    documented and example values. Use this as a starting point for
    customizing Redpen for your project.

    Examples:

        redpen config init

        redpen config init --output custom.toml

        redpen config init --stdout | less
    """
    if stdout:
        click.echo(EXAMPLE_CONFIG)
        return

    output_path = Path(output)
    if output_path.exists() and not force:
        console.print(
            f"[red]Error:[/red] {output} already exists. "
            "Use --force to overwrite."
        )
        raise SystemExit(1)

    output_path.write_text(EXAMPLE_CONFIG)
    console.print(f"[green]✓[/green] Configuration written to [cyan]{output}[/cyan]")
    console.print()
    console.print("Next steps:")
    console.print("  1. Edit the file to customize settings")
    console.print("  2. Run [cyan]redpen analyze <files>[/cyan] to use your config")
    console.print()
    console.print("Tips:")
    console.print("  • To disable curly quote suggestions, uncomment the line:")
    console.print('    [dim]"typography.symbols.curly_quotes"[/dim] in disabled_rules')
    console.print("  • To enable AI feedback, set [cyan]llm.enabled = true[/cyan]")


if __name__ == "__main__":
    cli()
