import os
import sys
from pathlib import Path
from typing import Annotated, Optional

import pydantic
import questionary
import rich
import typer

from shell_whiz.cli import AskCLI
from shell_whiz.config import Config, ConfigError, ConfigModel

app = typer.Typer(help="Shell Whiz: AI assistant for the command line")


@app.command()
def config():
    """Set up OpenAI API key"""

    try:
        config = ConfigModel(
            openai_api_key=questionary.text(
                "OpenAI API key",
                default=os.environ.get("OPENAI_API_KEY", ""),
                validate=lambda text: len(text) > 0,
            ).unsafe_ask()
        )
    except pydantic.ValidationError:
        rich.print("Something went wrong.", file=sys.stderr)
        sys.exit(1)

    try:
        Config.write(config)
    except ConfigError as e:
        rich.print(e, file=sys.stderr)
        sys.exit(1)


@app.command()
def ask(
    prompt: Annotated[list[str], typer.Argument(show_default=False)],
    preferences: Annotated[
        str,
        typer.Option(
            "-p", "--preferences", help="Preferences for the AI assistant."
        ),
    ] = "I use Bash on Linux.",
    model: Annotated[
        str, typer.Option(help="AI model to use.")
    ] = "gpt-3.5-turbo",
    explain_using: Annotated[
        Optional[str],
        typer.Option(
            help="AI model to use for explanation (defaults to --model).",
            show_default=False,
        ),
    ] = None,
    dont_warn: Annotated[
        bool, typer.Option(help="Skip the warning part.")
    ] = False,
    dont_explain: Annotated[
        bool,
        typer.Option(
            "-n",
            "--dont-explain/--no-dont-explain",
            help="Skip the explanation part.",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "-q", "--quiet/--no-quiet", help="Skip the interactive part."
        ),
    ] = False,
    shell: Annotated[
        Optional[Path],
        typer.Option(
            help="Shell to use for running the command. Defaults to the user's default shell.",
            dir_okay=False,
            show_default=False,
        ),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option(
            "-o",
            "--output",
            help="Instead of running the command, specify the output file for post-processing.",
            dir_okay=False,
            writable=True,
            show_default=False,
        ),
    ] = None,
):
    """Get assistance from AI"""

    explain_using = explain_using or model

    try:
        config = Config()
    except ConfigError:
        rich.print(
            "[bold yellow]Error[/]: Please set your OpenAI API key via [bold green]sw config[/] and try again.",
            file=sys.stderr,
        )
        sys.exit(1)

    AskCLI(
        openai_api_key=config.openai_api_key,
        openai_organization=config.openai_org_id,
        model=model,
        explain_using=explain_using,
        preferences=preferences,
    )(
        prompt=prompt,
        explain_using=explain_using,
        dont_warn=dont_warn,
        dont_explain=dont_explain,
        quiet=quiet,
        shell=shell,
        output=output,
    )


def run():
    app()
