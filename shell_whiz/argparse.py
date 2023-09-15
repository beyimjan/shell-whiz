import argparse
from importlib.metadata import version

from shell_whiz.constants import SW_DESCRIPTION


def create_argument_parser():
    parser = argparse.ArgumentParser(description=SW_DESCRIPTION)

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{SW_DESCRIPTION}. Version {version('shell-whiz')}.",
    )

    subparsers = parser.add_subparsers(dest="sw_command", required=True)

    subparsers.add_parser("config", help="Configure Shell Whiz")

    ask_parser = subparsers.add_parser(
        "ask", help="Ask Shell Whiz for a shell command"
    )
    ask_parser.add_argument(
        "-m",
        "--model",
        type=str,
        choices=["gpt-3.5-turbo", "gpt-4"],
        default="gpt-3.5-turbo",
        help="select the model to use",
    )
    ask_parser.add_argument(
        "--explain-using-gpt-4",
        action="store_true",
        help="use GPT-4 to explain",
    )
    ask_parser.add_argument(
        "-n",
        "--dont-explain",
        action="store_true",
        help="don't explain the command",
    )
    ask_parser.add_argument(
        "prompt", nargs="+", type=str, help="Prompt for Shell Whiz"
    )

    return parser
