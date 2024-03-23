import sys

import openai
import rich

from shell_whiz.cli import cli


def run() -> None:
    try:
        cli()
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
