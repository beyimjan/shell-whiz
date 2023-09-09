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

    ask_parser = subparsers.add_parser("ask", help="Ask Shell Whiz a question")
    ask_parser.add_argument(
        "prompt", nargs="+", type=str, help="Question to ask Shell Whiz"
    )

    return parser
