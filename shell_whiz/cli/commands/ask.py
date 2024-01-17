import asyncio
import os
import subprocess
import sys

import questionary
import rich
from rich.live import Live
from rich.markdown import Markdown
from rich.status import Status

from shell_whiz.llm import ClientLLM, ProviderOpenAI
from shell_whiz.llm.errors import (
    EditingError,
    ExplanationError,
    TranslationError,
    WarningError,
)


class AskCLI:
    __thinking_msg = ""

    def __init__(
        self,
        config,
        shell,
        preferences,
        model,
        explain_using,
        dont_explain,
        dont_warn,
        quiet,
        output,
    ):
        self.__dont_warn = dont_warn
        self.__dont_explain = dont_explain
        self.__quiet = quiet
        self.__output = output
        self.__shell = shell

        self.__choices = AskCLI.__get_actions(
            dont_explain, explain_using or model
        )

        self.__llm = ClientLLM(
            ProviderOpenAI(
                config["OPENAI_API_KEY"],
                model,
                preferences,
                explain_using=explain_using,
            )
        )

    async def __call__(self, prompt):
        try:
            with Status("Wait, Shell Whiz is thinking..."):
                shell_command = await self.__llm.suggest_shell_command(prompt)
        except TranslationError:
            rich.print("Sorry, I don't know how to do this.")
            sys.exit(1)

        while True:
            if not self.__dont_explain:
                self.__print_command(shell_command)
                stream_task = asyncio.create_task(
                    self.__llm.get_explanation_of_shell_command(
                        shell_command, True
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

            shell_command = await self.__perform_selected_action(
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
                cancel_run = (
                    is_dangerous
                    and not self.__view.confirm_running_dangerous_command()
                )
                if cancel_run:
                    continue

                if self.__output:
                    try:
                        with open(self.__output, "w", newline="\n") as f:
                            f.write(shell_command)
                    except os.error:
                        rich.print("Couldn't write to output file.")
                        sys.exit(1)
                else:
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
                    shell_command = await self.__edit_shell_command_cli(
                        shell_command, edit_prompt
                    )
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
    def __get_actions(dont_explain, explain_using) -> list[str]:
        actions = [
            "Run this command",
            "Explain this command",
            "Explain using GPT-4 Turbo [BETA]",
            "Explain using GPT-4",
            "Revise query",
            "Edit manually",
            "Exit",
        ]

        if not dont_explain:
            actions.remove("Explain this command")

        if explain_using == "gpt-4-1106-preview":
            actions.remove("Explain using GPT-4 Turbo [BETA]")
        elif explain_using == "gpt-4":
            actions.remove("Explain using GPT-4")

        return actions

    @staticmethod
    def __print_command(shell_command):
        rich.print(
            "\n ==================== [bold green]Command[/] ====================\n"
        )
        print(" " + " ".join(shell_command.splitlines(keepends=True)) + "\n")

    async def __recognize_dangerous_command(self, shell_command):
        with Status(
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
            with Status("Wait, Shell Whiz is thinking..."):
                shell_command = await self.__llm.edit_shell_command(
                    shell_command, prompt
                )
        except EditingError:
            rich.print(
                "\n  Sorry, I couldn't edit the command. I left it unchanged."
            )

        return shell_command