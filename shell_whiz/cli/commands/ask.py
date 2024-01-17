import asyncio
import os
import subprocess
import sys
from typing import Any

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


def _cat(shell_command: str) -> None:
    rich.print(
        "\n ==================== [bold green]Command[/] ====================\n"
    )
    print(" " + " ".join(shell_command.splitlines(keepends=True)) + "\n")


async def _explain(stream: Any) -> None:
    rich.print(
        " ================== [bold green]Explanation[/] =================="
    )

    try:
        with Live(auto_refresh=False) as live:
            explanation = ""
            async for chunk in stream:
                explanation += chunk
                live.update(Markdown(explanation), refresh=True)
    except ExplanationError:
        rich.print(" Sorry, I don't know how to explain this command.")

    print()


async def _run(
    shell_command: str, is_dangerous: bool, shell=None, output=None
):
    if is_dangerous:
        if not await questionary.confirm(
            "Are you sure you want to run this command?"
        ).unsafe_ask_async():
            return

    if output:
        try:
            with open(output, "w", newline="\n") as f:
                f.write(shell_command)
        except os.error:
            rich.print("Couldn't write to output file.")
            sys.exit(1)
    else:
        subprocess.run(shell_command, executable=shell, shell=True)

    sys.exit()


class AskCLI:
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

        self.__actions = [
            "Run this command",
            "Explain this command",
            "Explain using GPT-4 Turbo [BETA]",
            "Explain using GPT-4",
            "Revise query",
            "Edit manually",
            "Exit",
        ]

        if not dont_explain:
            self.__actions.remove("Explain this command")

        if explain_using == "gpt-4-1106-preview":
            self.__actions.remove("Explain using GPT-4 Turbo [BETA]")
        elif explain_using == "gpt-4":
            self.__actions.remove("Explain using GPT-4")

        self.__llm = ClientLLM(
            ProviderOpenAI(
                config["OPENAI_API_KEY"],
                model,
                preferences,
                explain_using=explain_using,
            )
        )

    async def __call__(self, prompt):
        await self.__suggest_shell_command(prompt)

        while True:
            await self.__warn_and_explain()
            if self.__quiet:
                break

            await self.__perform_selected_action()

    async def __suggest_shell_command(self, prompt):
        try:
            with Status("Wait, Shell Whiz is thinking..."):
                self.__shell_command = await self.__llm.suggest_shell_command(
                    prompt
                )
        except TranslationError:
            rich.print("Sorry, I don't know how to do this.")
            sys.exit(1)

    async def __warn_and_explain(self):
        if not self.__dont_explain:
            _cat(self.__shell_command)
            stream_task = asyncio.create_task(
                self.__llm.get_explanation_of_shell_command(
                    self.__shell_command, True
                )
            )

        if self.__dont_warn:
            self.__is_dangerous = False
        else:
            await self.__warn()

        if self.__dont_explain:
            _cat(self.__shell_command)

        if not self.__dont_warn and self.__is_dangerous:
            rich.print(
                " [bold red]Warning[/]: [bold yellow]{0}[/]\n".format(
                    self.__dangerous_consequences
                )
            )

        if not self.__dont_explain:
            await _explain(
                self.__llm.get_explanation_of_shell_command_by_chunks(
                    await stream_task
                )
            )

    async def __warn(self):
        try:
            with Status("Shell Whiz is checking the command for danger..."):
                (
                    self.__is_dangerous,
                    self.__dangerous_consequences,
                ) = await self.__llm.recognize_dangerous_command(
                    self.__shell_command
                )
        except WarningError:
            self.__is_dangerous = False

    async def __perform_selected_action(self):
        while True:
            action = await questionary.select(
                "Select an action", choices=self.__actions
            ).unsafe_ask_async()

            if action == "Exit":
                sys.exit(1)
            elif action == "Run this command":
                await _run(
                    self.__shell_command,
                    self.__is_dangerous,
                    shell=self.__shell,
                    output=self.__output,
                )
            elif action == "Explain this command":
                await _explain(
                    self.__llm.get_explanation_of_shell_command_by_chunks(
                        await self.__llm.get_explanation_of_shell_command(
                            self.__shell_command, True
                        )
                    )
                )
            elif action == "Explain using GPT-4 Turbo [BETA]":
                print()
                await _explain(
                    self.__llm.get_explanation_of_shell_command_by_chunks(
                        await self.__llm.get_explanation_of_shell_command(
                            self.__shell_command,
                            True,
                            explain_using="gpt-4-1106-preview",
                        )
                    )
                )
            elif action == "Explain using GPT-4":
                print()
                await _explain(
                    self.__llm.get_explanation_of_shell_command_by_chunks(
                        await self.__llm.get_explanation_of_shell_command(
                            self.__shell_command, True, explain_using="gpt-4"
                        )
                    )
                )
            elif action == "Revise query":
                self.__revise()
            elif action == "Edit manually":
                self.__edit_manually()

    async def __revise(self):
        prompt = (
            await questionary.text("Enter your revision").unsafe_ask_async()
        ).strip()

        if prompt == "":
            return

        try:
            with Status("Wait, Shell Whiz is thinking..."):
                shell_command = await self.__llm.edit_shell_command(
                    self.__shell_command, prompt
                )
        except EditingError:
            rich.print(
                "\n  Sorry, I couldn't edit the command. I left it unchanged."
            )

        return shell_command

    async def __edit_manually(self):
        res = (
            await questionary.text(
                "Edit command",
                default=self.__shell_command,
                multiline="\n" in self.__shell_command,
            ).unsafe_ask_async()
        ).strip()

        if res not in ("", self.__shell_command):
            self.__shell_command = res
