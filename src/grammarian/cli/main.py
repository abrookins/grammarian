"""Main CLI entry point for Grammarian."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from grammarian import __version__
from grammarian.calculator import Calculator
from grammarian.core.models import AnalysisResult, Rating

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
            title="✨ Grammarian Analysis Results",
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
    """Grammarian: A Drake Equation for English writing quality."""
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
    from grammarian.config import GrammarianConfig, DEFAULT_PROFILES
    from grammarian.metrics.grammar import GrammarMetric
    from grammarian.metrics.readability import ReadabilityMetric
    from grammarian.metrics.spelling import SpellingMetric
    from grammarian.metrics.style import StyleMetric

    # Load configuration
    config = GrammarianConfig.load(Path(config_path) if config_path else None)

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
        from grammarian.git import get_changed_files

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
        from grammarian.llm import WritingAdvisor

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


if __name__ == "__main__":
    cli()

