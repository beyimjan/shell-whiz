import subprocess
import sys

import inquirer
import rich
from inquirer.themes import GreenPassion
from openai import OpenAIError
from rich.markdown import Markdown

from shell_whiz.argparse import create_argument_parser
from shell_whiz.config import shell_whiz_config, shell_whiz_update_config
from shell_whiz.console import console
from shell_whiz.constants import OPENAI_CONNECTION_ERROR
from shell_whiz.exceptions import ShellWhizTranslationError
from shell_whiz.openai import (
    get_explanation_of_shell_command,
    translate_natural_language_to_shell_command,
)


def print_explanation():
    rich.print(
        " ================== [bold green]Explanation[/] =================="
    )


def print_command(shell_command, is_dangerous, dangerous_consequences):
    rich.print(
        "\n ==================== [bold green]Command[/] ====================\n"
    )

    for line in shell_command.splitlines():
        print(f" {line}")

    if is_dangerous:
        rich.print(
            f"\n[bold red] Warning:[/] [bold yellow]{dangerous_consequences}[/]"
        )

    print()


def shell_whiz_ask(prompt):
    try:
        (
            shell_command,
            is_dangerous,
            dangerous_consequences,
        ) = translate_natural_language_to_shell_command(prompt)
    except OpenAIError:
        rich.print(OPENAI_CONNECTION_ERROR, file=sys.stderr)
        sys.exit(2)
    except ShellWhizTranslationError:
        print("Shell Whiz doesn't understand your query.", file=sys.stderr)
        return

    print_command(shell_command, is_dangerous, dangerous_consequences)

    print_explanation()
    try:
        explanation = get_explanation_of_shell_command(shell_command)
        console.print(
            Markdown(
                explanation,
                inline_code_lexer="bash",
                inline_code_theme="lightbulb",
            )
        )
        print()
    except OpenAIError:
        print("\n Shell Whiz couldn't generate an explanation.\n")

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


def shell_whiz_explain(shell_command):
    try:
        explanation = get_explanation_of_shell_command(shell_command)
    except OpenAIError:
        rich.print(OPENAI_CONNECTION_ERROR, file=sys.stderr)
        sys.exit(2)

    print_explanation()
    console.print(Markdown(explanation))


def run_ai_assistant(args):
    shell_whiz_config()

    if args.sw_command == "ask":
        shell_command = " ".join(args.prompt).strip()
        if shell_command == "":
            print("Please provide a prompt.", file=sys.stderr)
            sys.exit(1)
        shell_whiz_ask(shell_command)
    elif args.sw_command == "explain":
        shell_command = " ".join(args.command).strip()
        if shell_command == "":
            print("Please provide a shell command.", file=sys.stderr)
            sys.exit(1)
        shell_whiz_explain(shell_command)


def main():
    args = create_argument_parser().parse_args()

    if args.sw_command == "config":
        shell_whiz_update_config()
    else:
        run_ai_assistant(args)


def run():
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
