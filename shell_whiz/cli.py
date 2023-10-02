import asyncio
import os
import subprocess
import sys

import openai
import questionary
import rich
from rich.live import Live
from rich.markdown import Markdown

from shell_whiz.argparse import create_argument_parser
from shell_whiz.config import sw_config, sw_edit_config
from shell_whiz.console import console
from shell_whiz.constants import SW_ERROR, SW_THINKING_MSG
from shell_whiz.exceptions import (
    ShellWhizEditError,
    ShellWhizExplanationError,
    ShellWhizTranslationError,
    ShellWhizWarningError,
)
from shell_whiz.openai import (
    edit_shell_command,
    get_explanation_of_shell_command,
    get_explanation_of_shell_command_openai_async,
    recognize_dangerous_command,
    translate_nl_to_shell_command,
)


async def print_explanation(
    explain_using_gpt_4, shell_command=None, stream_task=None, no_newline=True
):
    if not no_newline:
        print()

    rich.print(
        " ================== [bold green]Explanation[/] =================="
    )

    try:
        with Live("", auto_refresh=False) as live:
            explanation = ""
            for chunk in get_explanation_of_shell_command(
                explain_using_gpt_4,
                shell_command,
                await stream_task if stream_task else None,
            ):
                explanation += chunk
                live.update(Markdown(explanation), refresh=True)
    except ShellWhizExplanationError:
        rich.print(
            f" {SW_ERROR}: Sorry, I don't know how to explain this command."
        )

    print()


def print_command(shell_command):
    rich.print(
        "\n ==================== [bold green]Command[/] ====================\n"
    )
    print(" " + " ".join(shell_command.splitlines(keepends=True)) + "\n")


async def shell_whiz_edit(shell_command, prompt):
    try:
        with console.status(SW_THINKING_MSG, spinner="dots"):
            shell_command = await edit_shell_command(shell_command, prompt)
    except ShellWhizEditError:
        rich.print(
            f"\n {SW_ERROR}: Sorry, I couldn't edit the command. I left it unchanged."
        )

    return shell_command


def shell_whiz_check_danger(shell_command):
    with console.status(
        "Shell Whiz is checking the command for danger...", spinner="dots"
    ):
        try:
            return recognize_dangerous_command(shell_command)
        except ShellWhizWarningError:
            return False, ""


async def shell_whiz_ask_menu_choice(args):
    choices = [
        "Run this command",
        "Revise query",
        "Edit manually",
        "Exit",
    ]

    if args.dont_explain:
        choices.insert(1, "Explain this command")
        if not args.explain_using_gpt_4:
            choices.insert(2, "Explain using GPT-4")
    elif not args.explain_using_gpt_4:
        choices.insert(1, "Explain using GPT-4")

    choice = await questionary.select(
        "Select an action", choices
    ).unsafe_ask_async()

    return choice


async def shell_whiz_ask_menu(args, shell_command, is_dangerous):
    while True:
        choice = await shell_whiz_ask_menu_choice(args)

        if choice == "Exit":
            sys.exit(1)
        elif choice == "Run this command":
            if args.output:
                try:
                    with open(args.output, "w", newline="\n") as f:
                        f.write(shell_command)
                except IOError:
                    sys.exit(1)
            else:
                if (
                    is_dangerous
                    and not await questionary.confirm(
                        "Are you sure you want to run this command?"
                    ).unsafe_ask_async()
                ):
                    sys.exit(1)
                subprocess.run(
                    shell_command, executable=args.shell or None, shell=True
                )
            # End successfully only if the command has been executed
            sys.exit()
        elif choice.startswith("Explain"):
            await print_explanation(
                args.explain_using_gpt_4 or choice == "Explain using GPT-4",
                shell_command=shell_command,
                no_newline=False,
            )
        elif choice == "Revise query":
            edit_prompt = (
                await questionary.text(
                    message="Enter your revision"
                ).unsafe_ask_async()
            ).strip()
            if edit_prompt != "":
                return shell_command, edit_prompt
        elif choice == "Edit manually":
            edited_shell_command = (
                await questionary.text(
                    "Edit command",
                    default=shell_command,
                    multiline="\n" in shell_command,
                ).unsafe_ask_async()
            ).strip()
            if (
                edited_shell_command != ""
                and edited_shell_command != shell_command
            ):
                return edited_shell_command, ""


async def shell_whiz_ask(prompt, args):
    try:
        with console.status(SW_THINKING_MSG, spinner="dots"):
            shell_command = translate_nl_to_shell_command(prompt)
    except ShellWhizTranslationError:
        rich.print(f"{SW_ERROR}: Sorry, I don't know how to do this.")
        sys.exit(1)

    edit_prompt = ""
    while True:
        if edit_prompt != "":
            shell_command = await shell_whiz_edit(shell_command, edit_prompt)

        if not args.dont_explain:
            print_command(shell_command)
            stream_task = asyncio.create_task(
                get_explanation_of_shell_command_openai_async(
                    shell_command, args.explain_using_gpt_4
                )
            )

        if args.dont_warn:
            is_dangerous = False
        else:
            is_dangerous, dangerous_consequences = shell_whiz_check_danger(
                shell_command
            )

        if args.dont_explain:
            print_command(shell_command)

        if not args.dont_warn and is_dangerous:
            rich.print(
                " [bold red]Warning[/]: [bold yellow]{0}[/]\n".format(
                    dangerous_consequences
                )
            )

        if not args.dont_explain:
            await print_explanation(
                args.explain_using_gpt_4, stream_task=stream_task
            )

        if args.quiet:
            break

        shell_command, edit_prompt = await shell_whiz_ask_menu(
            args, shell_command, is_dangerous
        )


async def run_ai_assistant(args):
    await sw_config()

    os.environ["SW_MODEL"] = args.model
    os.environ["SW_PREFERENCES"] = args.preferences

    if args.model == "gpt-4":
        args.explain_using_gpt_4 = True

    prompt = " ".join(args.prompt).strip()
    if prompt == "":
        rich.print(f"{SW_ERROR}: Please provide a valid prompt.")
        sys.exit(1)

    await shell_whiz_ask(prompt, args)


async def main():
    args = create_argument_parser().parse_args()

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        try:
            rich.print(
                f"{SW_ERROR}: Shell Whiz cannot run in non-interactive mode."
            )
        except BrokenPipeError:
            pass

        sys.exit(1)

    if args.sw_command == "config":
        await sw_edit_config()
    elif args.sw_command == "ask":
        await run_ai_assistant(args)


def run():
    try:
        asyncio.run(main())
    except openai.error.APIError:
        rich.print(
            f"{SW_ERROR}: An error occurred while connecting to the OpenAI API. Please retry your request after a brief wait. The problem is on the side of the OpenAI. Visit https://status.openai.com for more information."
        )
        sys.exit(1)
    except openai.error.Timeout:
        rich.print(
            f"{SW_ERROR}: OpenAI API request timed out. Please retry your request after a brief wait."
        )
        sys.exit(1)
    except openai.error.APIConnectionError:
        rich.print(
            f"{SW_ERROR}: OpenAI API request failed to connect. Please check your internet connection and try again."
        )
        sys.exit(1)
    except openai.error.InvalidRequestError:
        rich.print(
            f"{SW_ERROR}: Your request was malformed or missing some required parameters, such as a token or an input."
        )
        sys.exit(1)
    except openai.error.AuthenticationError:
        rich.print(
            f"{SW_ERROR}: You are not authorized to access the OpenAI API. You may have entered the wrong API key. Your API key is invalid, expired or revoked. Please run [bold green]sw config[/] to set up the API key. Visit https://platform.openai.com/account/api-keys to get your API key."
        )
        sys.exit(1)
    except openai.error.PermissionError:
        rich.print(
            f"{SW_ERROR}: Your API key or token does not have the required scope or role to perform the requested action. Make sure your API key has the appropriate permissions for the action or model accessed."
        )
        sys.exit(1)
    except openai.error.RateLimitError:
        rich.print(
            f"{SW_ERROR}: OpenAI API request exceeded rate limit. If you are on a free plan, please upgrade to a paid plan for a better experience with Shell Whiz. Visit https://platform.openai.com/account/billing/limits for more information."
        )
        sys.exit(1)
    except openai.error.ServiceUnavailableError:
        rich.print(
            f"{SW_ERROR}: OpenAI API request failed due to a temporary server-side issue. Please retry your request after a brief wait. The problem is on the side of the OpenAI. Visit https://status.openai.com for more information."
        )
        sys.exit(1)
    except openai.error.OpenAIError:
        rich.print(
            f"{SW_ERROR}: An unknown error occurred while connecting to the OpenAI API. Please retry your request after a brief wait."
        )
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(1)
