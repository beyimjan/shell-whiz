import asyncio
import os
import sys
from pathlib import Path
from typing import Annotated, Optional

import openai
import pydantic
import questionary
import rich
import typer

from shell_whiz.cli import AskCLI
from shell_whiz.config import Config, ConfigError, ConfigModel

app = typer.Typer(help="Shell Whiz: AI assistant for the command line")


@app.command()
def config() -> None:
    """Set up OpenAI API key"""

    rich.print(
        "Visit https://platform.openai.com/api-keys to get your API key."
    )

    try:
        config = ConfigModel(
            openai_api_key=questionary.text(
                "OpenAI API key",
                default=os.environ.get("OPENAI_API_KEY", ""),
                validate=lambda text: len(text) > 0,
            ).unsafe_ask()
        )
    except pydantic.ValidationError:
        rich.print(
            "[bold yellow]Error[/]: Something went wrong.", file=sys.stderr
        )
        raise typer.Exit(1)

    try:
        Config.write(config)
    except ConfigError as e:
        rich.print(f"[bold yellow]Error[/]: {e}", file=sys.stderr)
        raise typer.Exit(1)


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
        str, typer.Option("-m", "--model", help="AI model to use.")
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
            "-s",
            "--shell",
            help="Shell for executing the command. On Unix-like systems, this is usually /bin/sh. In Windows, it is usually cmd.exe.",
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
) -> None:
    """Get assistance from AI"""

    explain_using = explain_using or model

    try:
        config = Config()
    except ConfigError:
        rich.print(
            "[bold yellow]Error[/]: Please set your OpenAI API key via [bold green]sw config[/] and try again.",
            file=sys.stderr,
        )
        raise typer.Exit(1)

    asyncio.run(
        AskCLI(
            openai_api_key=config.openai_api_key,
            openai_org_id=config.openai_org_id,
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
    )


def run() -> None:
    try:
        app()
    except openai.APITimeoutError:  # API connection error
        rich.print(
            "[bold yellow]Error[/]: OpenAI API request timed out. Please retry your request after a brief wait.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.BadRequestError:  # API status error
        rich.print(
            "[bold yellow]Error[/]: Your request was malformed or missing some required parameters, such as a token or an input.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.AuthenticationError:  # API status error
        rich.print(
            "[bold yellow]Error[/]: Check your API key and make sure it is correct and active. You may need to generate a new one from https://platform.openai.com/api-keys.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.PermissionDeniedError:  # API status error
        rich.print(
            "[bold yellow]Error[/]: Your API key does not have the required scope or role to perform the requested action. Make sure your API key has the appropriate permissions for the action or model accessed.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.RateLimitError:  # API status error
        rich.print(
            "[bold yellow]Error[/]: OpenAI API request exceeded rate limit. If you are on a free plan, please upgrade to a paid plan for a better experience. Visit https://platform.openai.com/account/limits for more information.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.InternalServerError:  # API status error
        rich.print(
            "[bold yellow]Error[/]: OpenAI API request failed due to a temporary server-side issue. Please retry your request after a brief wait. Visit https://status.openai.com for more information.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.APIConnectionError:
        rich.print(
            "[bold yellow]Error[/]: OpenAI API request failed to connect. Please check your internet connection and try again.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.APIStatusError:
        rich.print(
            "[bold yellow]Error[/]: An error occurred while connecting to the OpenAI API. Please retry your request after a brief wait. Visit https://status.openai.com for more information.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.APIError:
        rich.print(
            "[bold yellow]Error[/]: An unknown error occurred while connecting to the OpenAI API. Please retry your request after a brief wait.",
            file=sys.stderr,
        )
        sys.exit(1)
