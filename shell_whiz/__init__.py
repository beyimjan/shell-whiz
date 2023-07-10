import argparse
import subprocess
import sys

import inquirer
from inquirer.themes import GreenPassion
from openai import OpenAIError
from prompt_toolkit import prompt as pptk_prompt

from shell_whiz.config import shell_whiz_config, shell_whiz_update_config
from shell_whiz.exceptions import ShellWhizTranslationError
from shell_whiz.openai import translate_natural_language_to_shell_command

SHELL_WHIZ_DESCRIPTION = "Shell Whiz: AI assistant right in your terminal"


def shell_whiz_ask(prompt):
    prompt = prompt.strip()
    if prompt == "":
        prompt = pptk_prompt("Ask Shell Whiz: ")

    try:
        print()
        shell_command = translate_natural_language_to_shell_command(prompt)
    except OpenAIError:
        print("Couldn't connect to OpenAI API.", file=sys.stderr)
        sys.exit(2)
    except ShellWhizTranslationError:
        print("Shell Whiz doesn't understand your query.", file=sys.stderr)
        return

    questions = [
        inquirer.List(
            "action",
            message="Select an action",
            carousel=False,
            choices=["Run this command", "Exit"],
        )
    ]

    print(" ==================== Command ====================")
    print(f"\n {shell_command}\n")

    answers = inquirer.prompt(questions, theme=GreenPassion())
    choice = answers["action"]
    if choice == "Exit":
        sys.exit()
    elif choice == "Run this command":
        subprocess.run(shell_command, shell=True)


def main():
    parser = argparse.ArgumentParser(description=SHELL_WHIZ_DESCRIPTION)

    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser(
        "config", help="Configure Shell Whiz"
    )
    ask_parser = subparsers.add_parser("ask", help="Ask Shell Whiz a question")
    ask_parser.add_argument(
        "question", nargs="*", type=str, help="Question to ask Shell Whiz"
    )

    args = parser.parse_args()
    if args.command == "config":
        shell_whiz_update_config()
    elif args.command == "ask":
        shell_whiz_config()
        shell_whiz_ask(" ".join(args.question) if args.question else "")
