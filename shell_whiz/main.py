import asyncio
import os
import sys

import click
import openai
import questionary
import rich

from .cli import AskCLI
from .config import Config, WritingError


@click.group()
@click.version_option()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Shell Whiz: AI assistant for command line"""

    ctx.obj = Config()


@cli.command()
@click.pass_obj
def config(config: Config) -> None:
    """Set OpenAI API key"""

    rich.print(
        "Hello! I'm Shell Whiz, your AI assistant for the command line!\n\n"
        "Visit https://platform.openai.com/account/api-keys to get the API key."
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
        rich.print(f"\n[bold yellow]Error[/]: {e}", file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.option(
    "-s",
    "--shell",
    type=click.Path(dir_okay=False, executable=True),
    help="Set the shell executable.",
)
@click.option(
    "-p",
    "--preferences",
    type=str,
    default="I use Bash on Linux",
    help="Set your preferences (default: I use Bash on Linux).",
)
@click.option(
    "-m",
    "--model",
    type=str,
    default="gpt-3.5-turbo",
    help="Select the model to use (default: gpt-3.5-turbo).",
)
@click.option(
    "--explain-using",
    type=str,
    help="Select the model to explain (defaults to --model).",
)
@click.option(
    "-n", "--dont-explain", is_flag=True, help="Skip the explanation part."
)
@click.option("--dont-warn", is_flag=True, help="Skip the warning part.")
@click.option("-q", "--quiet", is_flag=True, help="Skip the interactive part.")
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, writable=True),
    help="Output file to write the command to.",
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
    """Ask for a shell command"""

    preferences = preferences.strip()
    if preferences == "":
        rich.print(
            "[bold yellow]Error[/]: Please provide your preferences.",
            file=sys.stderr,
        )
        exit(1)

    model = model.strip()
    if model == "":
        rich.print(
            "[bold yellow]Error[/]: Please provide a model.", file=sys.stderr
        )
        exit(1)

    if explain_using is None:
        explain_using = model
    elif explain_using.strip() == "":
        rich.print(
            "[bold yellow]Error[/]: Please provide a model to explain.",
            file=sys.stderr,
        )
        exit(1)

    prompt = " ".join(prompt).strip()
    if prompt == "":
        rich.print(
            "[bold yellow]Error[/]: Please provide a prompt.", file=sys.stderr
        )
        exit(1)

    if not config.data:
        rich.print(
            "[bold yellow]Error[/]: Please set your OpenAI API key via [bold green]sw config[/] and try again.",
            file=sys.stderr,
        )
        sys.exit(1)

    asyncio.run(
        AskCLI(config.data, model, preferences)(
            prompt,
            explain_using,
            dont_explain,
            dont_warn,
            quiet,
            shell,
            output,
        )
    )


def run() -> None:
    try:
        cli()
    except KeyboardInterrupt:
        print("\nAborted!")
        sys.exit(1)
    except openai.BadRequestError:
        rich.print(
            "[bold yellow]Error[/]: Your request was malformed or missing some required parameters, such as a token or an input.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.AuthenticationError:
        rich.print(
            "[bold yellow]Error[/]: You are not authorized to access the OpenAI API. You may have entered the wrong API key. Your API key is invalid, expired or revoked. Please run [bold green]sw config[/] to set up the API key. Visit https://platform.openai.com/account/api-keys to get your API key.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.PermissionDeniedError:
        rich.print(
            "[bold yellow]Error[/]: Your API key or token does not have the required scope or role to perform the requested action. Make sure your API key has the appropriate permissions for the action or model accessed.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.RateLimitError:
        rich.print(
            "[bold yellow]Error[/]: OpenAI API request exceeded rate limit. If you are on a free plan, please upgrade to a paid plan for a better experience with Shell Whiz. Visit https://platform.openai.com/account/billing/limits for more information.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.APITimeoutError:
        rich.print(
            "[bold yellow]Error[/]: OpenAI API request timed out. Please retry your request after a brief wait.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.APIConnectionError:
        rich.print(
            "[bold yellow]Error[/]: OpenAI API request failed to connect. Please check your internet connection and try again.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.InternalServerError:
        rich.print(
            "[bold yellow]Error[/]: OpenAI API request failed due to a temporary server-side issue. Please retry your request after a brief wait. The problem is on the side of the OpenAI. Visit https://status.openai.com for more information.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.APIStatusError:
        rich.print(
            "[bold yellow]Error[/]: An error occurred while connecting to the OpenAI API. Please retry your request after a brief wait. The problem is on the side of the OpenAI. Visit https://status.openai.com for more information.",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.APIError:
        rich.print(
            "[bold yellow]Error[/]: An unknown error occurred while connecting to the OpenAI API. Please retry your request after a brief wait.",
            file=sys.stderr,
        )
        sys.exit(1)
