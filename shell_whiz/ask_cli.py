import asyncio
import subprocess
import sys

import questionary
import rich
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from .config_cli import ConfigCLI
from .llm import ClientLLM, ClientOpenAI
from .llm.errors import (
    EditingError,
    ExplanationError,
    TranslationError,
    WarningError,
)


class AskCLI:
    __thinking_msg = "Wait, Shell Whiz is thinking..."

    def __init__(
        self,
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
        self.__shell = shell
        self.__preferences = preferences
        self.__model = model
        self.__explain_using = explain_using
        self.__dont_explain = dont_explain
        self.__dont_warn = dont_warn
        self.__quiet = quiet
        self.__output_file = output
        self.__prompt = prompt

        self.__choices = AskCLI.__get_choices(dont_explain, explain_using)

        self.__console = Console()

    async def __call__(self):
        config = await ConfigCLI().get()

        self.__llm = ClientLLM(
            ClientOpenAI(
                config["OPENAI_API_KEY"],
                self.__model,
                self.__preferences,
                explain_using=self.__explain_using,
            )
        )

        try:
            with self.__console.status(self.__thinking_msg, spinner="dots"):
                shell_command = await self.__llm.suggest_shell_command(
                    self.__prompt
                )
        except TranslationError:
            rich.print("Sorry, I don't know how to do this.")
            sys.exit(1)

        edit_prompt = ""
        while True:
            if edit_prompt != "":
                shell_command = await self.__edit_shell_command_cli(
                    shell_command, edit_prompt
                )

            if not self.__dont_explain:
                self.__print_command(shell_command)
                stream_task = asyncio.create_task(
                    self.__llm.get_explanation_of_shell_command(
                        shell_command, stream=True
                    )
                )

            if self.__dont_warn:
                is_dangerous = False
            else:
                (
                    is_dangerous,
                    dangerous_consequences,
                ) = await self.__recognize_dangerous_command(shell_command)

            if self.__dont_explain:
                self.__print_command(shell_command)

            if not self.__dont_warn and is_dangerous:
                rich.print(
                    " [bold red]Warning[/]: [bold yellow]{0}[/]\n".format(
                        dangerous_consequences
                    )
                )

            if not self.__dont_explain:
                await self.__print_explanation(
                    shell_command, stream=await stream_task
                )

            if self.__quiet:
                break

            shell_command, edit_prompt = await self.__perform_selected_action(
                shell_command, is_dangerous
            )

    async def __perform_selected_action(self, shell_command, is_dangerous):
        while True:
            choice = await questionary.select(
                "Select an action", choices=self.__choices
            ).unsafe_ask_async()

            if choice == "Exit":
                sys.exit(1)
            elif choice == "Run this command":
                if self.__output_file:
                    try:
                        with open(self.__output_file, "w", newline="\n") as f:
                            f.write(shell_command)
                    except OSError:
                        rich.print("Couldn't write to output file.")
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
                    subprocess.run(
                        shell_command, executable=self.__shell, shell=True
                    )
                # End successfully only if the command has been executed
                sys.exit()
            elif choice == "Explain this command":
                await self.__print_explanation(shell_command)
            elif choice == "Explain using GPT-4 Turbo [BETA]":
                await self.__print_explanation(
                    shell_command,
                    explain_using="gpt-4-1106-preview",
                    insert_newline=True,
                )
            elif choice == "Explain using GPT-4":
                await self.__print_explanation(
                    shell_command=shell_command,
                    explain_using="gpt-4",
                    insert_newline=True,
                )
            elif choice == "Revise query":
                edit_prompt = (
                    await questionary.text(
                        "Enter your revision"
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

    @staticmethod
    def __get_choices(dont_explain, explain_using):
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

        if explain_using == "gpt-4-1106-preview":
            choices.remove("Explain using GPT-4 Turbo [BETA]")
        elif explain_using == "gpt-4":
            choices.remove("Explain using GPT-4")

        return choices

    @staticmethod
    def __print_command(shell_command):
        rich.print(
            "\n ==================== [bold green]Command[/] ====================\n"
        )
        print(" " + " ".join(shell_command.splitlines(keepends=True)) + "\n")

    async def __recognize_dangerous_command(self, shell_command):
        with self.__console.status(
            "Shell Whiz is checking the command for danger...", spinner="dots"
        ):
            try:
                return await self.__llm.recognize_dangerous_command(
                    shell_command
                )
            except WarningError:
                return False, ""

    async def __print_explanation(
        self,
        shell_command: str,
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
                async for chunk in self.__llm.get_explanation_of_shell_command_by_chunks(
                    stream
                    or await self.__llm.get_explanation_of_shell_command(
                        shell_command, explain_using=explain_using, stream=True
                    )
                ):
                    explanation += chunk
                    live.update(Markdown(explanation), refresh=True)
        except ExplanationError:
            rich.print(" Sorry, I don't know how to explain this command.")

        print()

    async def __edit_shell_command_cli(self, shell_command, prompt):
        try:
            with self.__console.status(self.__thinking_msg, spinner="dots"):
                shell_command = await self.__llm.edit_shell_command(
                    shell_command, prompt
                )
        except EditingError:
            rich.print(
                "\n  Sorry, I couldn't edit the command. I left it unchanged."
            )

        return shell_command
