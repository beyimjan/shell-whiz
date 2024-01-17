import asyncio
import os
import sys

import click
import questionary
import rich
from rich.console import Console

from .cli import AskCLI
from .config import Config, WritingError


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Shell Whiz: AI assistant for command line"""

    ctx.obj = Config()


@cli.command()
@click.pass_obj
def config(config: Config) -> None:
    """Set OpenAI API key."""

    _config(config)


def _config(config: Config) -> None:
    rich.print(
        "Visit https://platform.openai.com/account/api-keys to get your API key."
    )

    try:
        config.write(
            {
                "OPENAI_API_KEY": questionary.text(
                    "OpenAI API key",
                    default=os.environ.get("OPENAI_API_KEY", ""),
                    validate=lambda text: len(text) > 0,
                ).unsafe_ask()
            }
        )
    except WritingError as e:
        rich.print(f"[bold yellow]Error[/]: {e}", file=sys.stderr)


@cli.command()
@click.option("-s", "--shell", type=str, help="Set the shell executable")
@click.option(
    "-p",
    "--preferences",
    type=str,
    default="I use Bash on Linux",
    help="Set your preferences (default: I use Bash on Linux)",
)
@click.option(
    "-m",
    "--model",
    type=str,
    default="gpt-3.5-turbo",
    help="Select the model to use (default: gpt-3.5-turbo)",
)
@click.option(
    "--explain-using",
    type=str,
    help="Select the model to explain (defaults to --model)",
)
@click.option(
    "-n", "--dont-explain", is_flag=True, help="Don't explain the command"
)
@click.option(
    "--dont-warn", is_flag=True, help="Don't warn about dangerous commands"
)
@click.option(
    "-q", "--quiet", is_flag=True, help="Don't show the menu, end immediately"
)
@click.option(
    "-o", "--output", type=str, help="Output file to write the command to"
)
@click.argument("prompt", nargs=-1, required=True)
@click.pass_obj
def ask(
    config: Config,
    shell,
    preferences,
    model,
    explain_using,
    dont_explain,
    dont_warn,
    quiet,
    output,
    prompt,
) -> None:
    """Ask for a shell command."""

    prompt = " ".join(prompt).strip()
    if prompt == "":
        rich.print(
            "[bold yellow]Error[/]: Please provide a prompt.", file=sys.stderr
        )
        exit(1)

    if not config.data:
        _config(config)

    asyncio.run(
        AskCLI(
            config.data,
            shell,
            preferences,
            model,
            explain_using,
            dont_explain,
            dont_warn,
            quiet,
            output,
        )(prompt)
    )


def run():
    try:
        if sys.stdin.isatty() and sys.stdout.isatty():
            cli()
        else:
            rich.print(
                "[bold yellow]Error[/]: Working in non-interactive mode is not supported.",
                file=sys.stderr,
            )
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted!")
        sys.exit(1)
