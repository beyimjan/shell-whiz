import asyncio
import sys

import click
import openai

from .ask_cli import AskCLI
from .cli_tools import pretty_log_error
from .config_cli import ConfigCLI


@click.group()
def cli():
    """Shell Whiz: AI assistant for command line"""
    pass


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
def ask(
    shell,
    preferences,
    model,
    explain_using,
    dont_explain,
    dont_warn,
    quiet,
    output,
    prompt,
):
    """Ask Shell Whiz for a shell command"""
    prompt = " ".join(prompt).strip()
    if prompt == "":
        pretty_log_error("Please provide a valid prompt.")
        exit(1)

    asyncio.run(
        AskCLI(
            shell,
            preferences,
            model,
            explain_using,
            dont_explain,
            dont_warn,
            quiet,
            output,
            prompt,
        )()
    )


@cli.command()
def config():
    """Configure Shell Whiz"""
    asyncio.run(ConfigCLI()())


def run():
    try:
        if sys.stdin.isatty() and sys.stdout.isatty():
            cli()
        else:
            pretty_log_error("Shell Whiz cannot run in non-interactive mode.")
    except KeyboardInterrupt:
        print("\nExiting...")
    except openai.BadRequestError:
        pretty_log_error(
            "Your request was malformed or missing some required parameters, such as a token or an input."
        )
    except openai.AuthenticationError:
        pretty_log_error(
            "You are not authorized to access the OpenAI API. You may have entered the wrong API key. Your API key is invalid, expired or revoked. Please run [bold green]sw config[/] to set up the API key. Visit https://platform.openai.com/account/api-keys to get your API key."
        )
    except openai.PermissionDeniedError:
        pretty_log_error(
            "Your API key or token does not have the required scope or role to perform the requested action. Make sure your API key has the appropriate permissions for the action or model accessed."
        )
    except openai.RateLimitError:
        pretty_log_error(
            "OpenAI API request exceeded rate limit. If you are on a free plan, please upgrade to a paid plan for a better experience with Shell Whiz. Visit https://platform.openai.com/account/billing/limits for more information."
        )
    except openai.APITimeoutError:
        pretty_log_error(
            "OpenAI API request timed out. Please retry your request after a brief wait."
        )
    except openai.APIConnectionError:
        pretty_log_error(
            "OpenAI API request failed to connect. Please check your internet connection and try again."
        )
    except openai.InternalServerError:
        pretty_log_error(
            "OpenAI API request failed due to a temporary server-side issue. Please retry your request after a brief wait. The problem is on the side of the OpenAI. Visit https://status.openai.com for more information."
        )
    except openai.APIStatusError:
        pretty_log_error(
            "An error occurred while connecting to the OpenAI API. Please retry your request after a brief wait. The problem is on the side of the OpenAI. Visit https://status.openai.com for more information."
        )
    except openai.APIError:
        pretty_log_error(
            "An unknown error occurred while connecting to the OpenAI API. Please retry your request after a brief wait."
        )
    sys.exit(1)
