import argparse
import subprocess
import sys

import colorama
import inquirer
from colorama import Fore, Style
from inquirer.themes import GreenPassion
from openai import OpenAIError
from prompt_toolkit import prompt as pptk_prompt

from shell_whiz.config import shell_whiz_config, shell_whiz_update_config
from shell_whiz.constants import (
    OPENAI_CONNECTION_ERROR,
    SHELL_WHIZ_DESCRIPTION,
)
from shell_whiz.exceptions import (
    ShellWhizExplanationError,
    ShellWhizTranslationError,
)
from shell_whiz.openai import (
    get_explanation_of_shell_command,
    translate_natural_language_to_shell_command,
)


def print_explanation(explanation):
    print(
        " ================== "
        + f"{Fore.GREEN}Explanation{Style.RESET_ALL}"
        + " ==================\n"
    )
    print(explanation)


def shell_whiz_ask(prompt):
    prompt = prompt.strip()
    if prompt == "":
        prompt = pptk_prompt("Ask Shell Whiz: ")

    try:
        print()
        shell_command = translate_natural_language_to_shell_command(prompt)
    except OpenAIError:
        print(OPENAI_CONNECTION_ERROR, file=sys.stderr)
        sys.exit(2)
    except ShellWhizTranslationError:
        print("Shell Whiz doesn't understand your query.", file=sys.stderr)
        return

    print(
        " ==================== "
        + f"{Fore.GREEN}Command{Style.RESET_ALL}"
        + " ===================="
    )
    print(f"\n {shell_command}\n")

    print(
        " ================== "
        + f"{Fore.GREEN}Explanation{Style.RESET_ALL}"
        + " ==================\n"
    )
    try:
        explanation = get_explanation_of_shell_command(shell_command)
        print(explanation)
    except OpenAIError:
        print(OPENAI_CONNECTION_ERROR, file=sys.stderr)
        sys.exit(2)
    except ShellWhizExplanationError:
        print(" Shell Whiz couldn't generate an explanation.\n")

    questions = [
        inquirer.List(
            "action",
            message="Select an action",
            carousel=False,
            choices=["Run this command", "Exit"],
        )
    ]

    answers = inquirer.prompt(questions, theme=GreenPassion())
    choice = answers["action"]
    if choice == "Exit":
        sys.exit()
    elif choice == "Run this command":
        subprocess.run(shell_command, shell=True)


def shell_whiz_explain(prompt):
    prompt = prompt.strip()
    if prompt == "":
        prompt = pptk_prompt("Command to explain: ")

    try:
        print()
        explanation = get_explanation_of_shell_command(prompt)
    except OpenAIError:
        print(OPENAI_CONNECTION_ERROR, file=sys.stderr)
        sys.exit(2)
    except ShellWhizExplanationError:
        print("Shell Whiz couldn't generate an explanation.", file=sys.stderr)
        return

    print_explanation(explanation)


def main():
    parser = argparse.ArgumentParser(description=SHELL_WHIZ_DESCRIPTION)

    subparsers = parser.add_subparsers(dest="sw_command", required=True)

    config_parser = subparsers.add_parser(
        "config", help="Configure Shell Whiz"
    )
    ask_parser = subparsers.add_parser("ask", help="Ask Shell Whiz a question")
    ask_parser.add_argument(
        "question", nargs="*", type=str, help="Question to ask Shell Whiz"
    )

    explain_parser = subparsers.add_parser(
        "explain", help="Explain a shell command"
    )
    explain_parser.add_argument(
        "command", nargs="*", type=str, help="Shell command to explain"
    )

    args = parser.parse_args()

    colorama.init()
    if args.sw_command == "config":
        shell_whiz_update_config()
    elif args.sw_command == "ask":
        shell_whiz_config()
        shell_whiz_ask(" ".join(args.question) if args.question else "")
    elif args.sw_command == "explain":
        shell_whiz_config()
        shell_whiz_explain(" ".join(args.command) if args.command else "")
