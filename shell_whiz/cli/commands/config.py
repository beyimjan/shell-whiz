import os
import sys

import pydantic
import questionary
import rich
import typer

from shell_whiz.config import Config, ConfigError, ConfigModel


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
