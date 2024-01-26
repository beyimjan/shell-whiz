import asyncio
import subprocess
import sys

import openai
import questionary
import rich
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from shell_whiz.argparse import create_argument_parser
from shell_whiz.config import configure, edit_config
from shell_whiz.constants import ERROR_PREFIX_RICH, THINKING_MSG
from shell_whiz.exceptions import (
    EditingError,
    ExplanationError,
    TranslationError,
    WarningError,
)
from shell_whiz.llm_client import (
    edit_shell_command,
    get_explanation_of_shell_command,
    get_explanation_of_shell_command_by_chunks,
    recognize_dangerous_command,
    suggest_shell_command,
)

console = Console()


def print_command(shell_command):
    rich.print(
        "\n ==================== [bold green]Command[/] ====================\n"
    )
    print(" " + " ".join(shell_command.splitlines(keepends=True)) + "\n")


async def check_danger(shell_command, preferences, model):
    with console.status(
        "Shell Whiz is checking the command for danger...", spinner="dots"
    ):
        try:
            return await recognize_dangerous_command(
                shell_command=shell_command,
                preferences=preferences,
                model=model,
            )
        except WarningError:
            return False, ""


async def print_explanation(
    shell_command=None,
    preferences=None,
    explain_using=None,
    stream=None,
    insert_newline=False,
):
    if insert_newline:
        print()

    rich.print(
        " ================== [bold green]Explanation[/] =================="
    )

    try:
        with Live("", auto_refresh=False) as live:
            explanation = ""
            async for chunk in get_explanation_of_shell_command_by_chunks(
                shell_command=shell_command,
                preferences=preferences,
                model=explain_using,
                stream=stream,
            ):
                explanation += chunk
                live.update(Markdown(explanation), refresh=True)
    except ExplanationError:
        rich.print(
            f" {ERROR_PREFIX_RICH}: Sorry, I don't know how to explain this command."
        )

    print()


async def edit_shell_command_cli(shell_command, prompt, model):
    try:
        with console.status(THINKING_MSG, spinner="dots"):
            shell_command = await edit_shell_command(
                shell_command=shell_command, prompt=prompt, model=model
            )
    except EditingError:
        rich.print(
            f"\n {ERROR_PREFIX_RICH}: Sorry, I couldn't edit the command. I left it unchanged."
        )

    return shell_command


def get_filtered_choices(dont_explain, explain_using):
    choices = [
        "Run this command",
        "Explain this command",
        "Explain using GPT-4 Turbo [BETA]",
        "Explain using GPT-4",
        "Revise query",
        "Edit manually",
        "Exit",
    ]

    if not dont_explain:
        choices.remove("Explain this command")

    if explain_using == "gpt-4-turbo-preview":
        choices.remove("Explain using GPT-4 Turbo [BETA]")
    elif explain_using == "gpt-4":
        choices.remove("Explain using GPT-4")

    return choices


async def perform_selected_action(
    shell_command,
    is_dangerous,
    preferences,
    explain_using,
    shell,
    dont_explain,
    output_file,
):
    while True:
        choice = await questionary.select(
            "Select an action",
            choices=get_filtered_choices(
                dont_explain=dont_explain, explain_using=explain_using
            ),
        ).unsafe_ask_async()

        if choice == "Exit":
            sys.exit(1)
        elif choice == "Run this command":
            if output_file:
                try:
                    with open(output_file, "w", newline="\n") as f:
                        f.write(shell_command)
                except OSError:
                    rich.print(
                        f"{ERROR_PREFIX_RICH}: Couldn't write to output file."
                    )
                    sys.exit(1)
            else:
                cancel_run = (
                    is_dangerous
                    and not await questionary.confirm(
                        "Are you sure you want to run this command?"
                    ).unsafe_ask_async()
                )
                if cancel_run:
                    sys.exit(1)
                subprocess.run(shell_command, executable=shell, shell=True)
            # End successfully only if the command has been executed
            sys.exit()
        elif choice == "Explain this command":
            await print_explanation(
                shell_command=shell_command,
                preferences=preferences,
                explain_using=explain_using,
                insert_newline=True,
            )
        elif choice == "Explain using GPT-4 Turbo [BETA]":
            await print_explanation(
                shell_command=shell_command,
                preferences=preferences,
                explain_using="gpt-4-turbo-preview",
                insert_newline=True,
            )
        elif choice == "Explain using GPT-4":
            await print_explanation(
                shell_command=shell_command,
                preferences=preferences,
                explain_using="gpt-4",
                insert_newline=True,
            )
        elif choice == "Revise query":
            edit_prompt = (
                await questionary.text("Enter your revision").unsafe_ask_async()
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


async def run_ai_assistant(
    prompt,
    preferences,
    model,
    explain_using,
    dont_explain,
    dont_warn,
    quiet,
    shell,
    output_file,
):
    await configure()

    try:
        with console.status(THINKING_MSG, spinner="dots"):
            shell_command = await suggest_shell_command(
                prompt=prompt, preferences=preferences, model=model
            )
    except TranslationError:
        rich.print(f"{ERROR_PREFIX_RICH}: Sorry, I don't know how to do this.")
        sys.exit(1)

    edit_prompt = ""
    while True:
        if edit_prompt != "":
            shell_command = await edit_shell_command_cli(
                shell_command=shell_command, prompt=edit_prompt, model=model
            )

        if not dont_explain:
            print_command(shell_command)
            stream_task = asyncio.create_task(
                get_explanation_of_shell_command(
                    shell_command=shell_command,
                    preferences=preferences,
                    model=explain_using,
                    stream=True,
                )
            )

        if dont_warn:
            is_dangerous = False
        else:
            is_dangerous, dangerous_consequences = await check_danger(
                shell_command=shell_command,
                preferences=preferences,
                model=model,
            )

        if dont_explain:
            print_command(shell_command)

        if not dont_warn and is_dangerous:
            rich.print(
                " [bold red]Warning[/]: [bold yellow]{0}[/]\n".format(
                    dangerous_consequences
                )
            )

        if not dont_explain:
            await print_explanation(stream=await stream_task)

        if quiet:
            break

        shell_command, edit_prompt = await perform_selected_action(
            shell_command=shell_command,
            is_dangerous=is_dangerous,
            preferences=preferences,
            explain_using=explain_using,
            shell=shell,
            dont_explain=dont_explain,
            output_file=output_file,
        )


async def parse_arguments():
    args = create_argument_parser().parse_args()

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        try:
            rich.print(
                f"{ERROR_PREFIX_RICH}: Shell Whiz cannot run in non-interactive mode."
            )
        except BrokenPipeError:
            pass

        sys.exit(1)

    if args.command == "config":
        await edit_config()
    elif args.command == "ask":
        prompt = " ".join(args.prompt).strip()
        if prompt == "":
            rich.print(f"{ERROR_PREFIX_RICH}: Please provide a valid prompt.")
            sys.exit(1)

        await run_ai_assistant(
            prompt=prompt,
            preferences=args.preferences,
            model=args.model,
            explain_using=args.explain_using or args.model,
            dont_explain=args.dont_explain,
            dont_warn=args.dont_warn,
            quiet=args.quiet,
            shell=args.shell,
            output_file=args.output,
        )


def run():
    try:
        asyncio.run(parse_arguments())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(1)
    except openai.BadRequestError:
        rich.print(
            f"{ERROR_PREFIX_RICH}: Your request was malformed or missing some required parameters, such as a token or an input."
        )
        sys.exit(1)
    except openai.AuthenticationError:
        rich.print(
            f"{ERROR_PREFIX_RICH}: You are not authorized to access the OpenAI API. You may have entered the wrong API key. Your API key is invalid, expired or revoked. Please run [bold green]sw config[/] to set up the API key. Visit https://platform.openai.com/account/api-keys to get your API key."
        )
        sys.exit(1)
    except openai.PermissionDeniedError:
        rich.print(
            f"{ERROR_PREFIX_RICH}: Your API key or token does not have the required scope or role to perform the requested action. Make sure your API key has the appropriate permissions for the action or model accessed."
        )
        sys.exit(1)
    except openai.RateLimitError:
        rich.print(
            f"{ERROR_PREFIX_RICH}: OpenAI API request exceeded rate limit. If you are on a free plan, please upgrade to a paid plan for a better experience with Shell Whiz. Visit https://platform.openai.com/account/billing/limits for more information."
        )
        sys.exit(1)
    except openai.APITimeoutError:
        rich.print(
            f"{ERROR_PREFIX_RICH}: OpenAI API request timed out. Please retry your request after a brief wait."
        )
        sys.exit(1)
    except openai.APIConnectionError:
        rich.print(
            f"{ERROR_PREFIX_RICH}: OpenAI API request failed to connect. Please check your internet connection and try again."
        )
        sys.exit(1)
    except openai.InternalServerError:
        rich.print(
            f"{ERROR_PREFIX_RICH}: OpenAI API request failed due to a temporary server-side issue. Please retry your request after a brief wait. The problem is on the side of the OpenAI. Visit https://status.openai.com for more information."
        )
        sys.exit(1)
    except openai.APIStatusError:
        rich.print(
            f"{ERROR_PREFIX_RICH}: An error occurred while connecting to the OpenAI API. Please retry your request after a brief wait. The problem is on the side of the OpenAI. Visit https://status.openai.com for more information."
        )
        sys.exit(1)
    except openai.APIError:
        rich.print(
            f"{ERROR_PREFIX_RICH}: An unknown error occurred while connecting to the OpenAI API. Please retry your request after a brief wait."
        )
        sys.exit(1)
