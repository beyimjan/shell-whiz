import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, NoReturn, Optional

import questionary
import rich
import typer
from rich.live import Live
from rich.markdown import Markdown
from rich.status import Status

from shell_whiz.llm import (
    ClientLLM,
    EditingError,
    ExplanationError,
    ProviderOpenAI,
    SuggestionError,
    WarningError,
)


class _CMD:
    shell_command: str
    is_dangerous: bool = False
    dangerous_consequences: str = ""

    def __init__(self, shell_command: str) -> None:
        self.shell_command = shell_command

    def cat(self) -> None:
        rich.print(
            "\n ==================== [bold green]Command[/] ====================\n"
        )
        print(
            " " + " ".join(self.shell_command.splitlines(keepends=True)) + "\n"
        )

    def warn(self) -> None:
        if self.is_dangerous:
            rich.print(
                " [bold red]Warning[/]: [bold yellow]{0}[/]\n".format(
                    self.dangerous_consequences
                )
            )

    @staticmethod
    async def explain(stream: Any) -> None:
        rich.print(
            " ================== [bold green]Explanation[/] =================="
        )

        with Live(auto_refresh=False) as live:
            explanation = ""
            async for chunk in stream:
                explanation += chunk
                live.update(Markdown(explanation), refresh=True)

        print()

    async def run(
        self, shell: Optional[Path] = None, output: Optional[Path] = None
    ) -> NoReturn:
        if self.is_dangerous:
            if not await questionary.confirm(
                "Are you sure you want to run this command?"
            ).unsafe_ask_async():
                raise typer.Exit(1)

        if output:
            try:
                with open(output, mode="w", newline="\n") as f:
                    f.write(self.shell_command)
            except os.error:
                rich.print(
                    "[bold yellow]Error[/]: Failed to write to the output file.",
                    file=sys.stderr,
                )
                raise typer.Exit(1)
        else:
            subprocess.run(self.shell_command, executable=shell, shell=True)

        raise typer.Exit()

    async def edit(self) -> None:
        res = await questionary.text(
            "Edit command",
            default=self.shell_command,
            multiline="\n" in self.shell_command,
        ).unsafe_ask_async()

        if res not in ("", self.shell_command):
            self.shell_command = res


class AskCLI:
    def __init__(
        self,
        *,
        openai_api_key: str,
        model: str,
        explain_using: str,
        preferences: str,
        openai_org_id: Optional[str] = None,
    ) -> None:
        self.__llm = ClientLLM(
            ProviderOpenAI(
                api_key=openai_api_key,
                organization=openai_org_id,
                model=model,
                explain_using=explain_using,
                preferences=preferences,
            )
        )

    async def __call__(
        self,
        *,
        prompt: list[str],
        explain_using: str,
        dont_warn: bool,
        dont_explain: bool,
        quiet: bool,
        shell: Optional[Path] = None,
        output: Optional[Path] = None,
    ) -> None:
        try:
            with Status("Wait, Shell Whiz is thinking..."):
                cmd = _CMD(
                    await self.__llm.suggest_shell_command(" ".join(prompt))
                )
        except SuggestionError:
            rich.print(
                "[bold yellow]Error[/]: Sorry, I don't know how to do this.",
                file=sys.stderr,
            )
            raise typer.Exit(1)

        actions = AskCLI.__get_actions(explain_using, dont_explain)
        while True:
            if not dont_explain:
                cmd.cat()
                explanation = asyncio.create_task(
                    self.__llm.get_explanation_of_shell_command(
                        cmd.shell_command
                    )
                )

            if dont_warn:
                cmd.is_dangerous = False
            else:
                try:
                    with Status("Wait, Shell Whiz is thinking..."):
                        (
                            cmd.is_dangerous,
                            cmd.dangerous_consequences,
                        ) = await self.__llm.recognise_dangerous_command(
                            cmd.shell_command
                        )
                except WarningError:
                    cmd.is_dangerous = False

            if dont_explain:
                cmd.cat()

            if not dont_warn:
                cmd.warn()

            if not dont_explain:
                await self.__explain_shell_command(explanation)

            if quiet:
                break

            await self.__perform_selected_action(cmd, actions, shell, output)

    async def __perform_selected_action(
        self,
        cmd: _CMD,
        actions: list[str],
        shell: Optional[Path] = None,
        output: Optional[Path] = None,
    ) -> None:
        while True:
            action = await questionary.select(
                "Select an action", actions
            ).unsafe_ask_async()

            if action == "Exit":
                raise typer.Exit(1)
            elif action == "Run this command":
                await cmd.run(shell, output)
            elif action == "Explain this command":
                print()
                await self.__explain_shell_command(
                    self.__llm.get_explanation_of_shell_command(
                        cmd.shell_command
                    )
                )
            elif action == "Explain using GPT-4":
                print()
                await self.__explain_shell_command(
                    self.__llm.get_explanation_of_shell_command(
                        cmd.shell_command, explain_using="gpt-4-turbo-preview"
                    )
                )
            elif action == "Revise query":
                cmd.shell_command = await self.__edit_shell_command(
                    cmd.shell_command
                )
                return
            elif action == "Edit manually":
                await cmd.edit()
                return

    @staticmethod
    def __get_actions(explain_using: str, dont_explain: bool) -> list[str]:
        actions = [
            "Run this command",
            "Explain this command",
            "Explain using GPT-4",
            "Revise query",
            "Edit manually",
            "Exit",
        ]

        if not dont_explain:
            actions.remove("Explain this command")

        if explain_using.startswith("gpt-4"):
            actions.remove("Explain using GPT-4")

        return actions

    async def __explain_shell_command(self, coro: Any) -> None:
        with Status("Wait, Shell Whiz is thinking..."):
            stream = await coro

        try:
            await _CMD.explain(
                self.__llm.get_explanation_of_shell_command_by_chunks(stream)
            )
        except ExplanationError:
            rich.print(" Sorry, I don't know how to explain this command.\n")

    async def __edit_shell_command(self, shell_command: str) -> str:
        prompt = await questionary.text(
            "Enter your revision", validate=lambda x: x != ""
        ).unsafe_ask_async()

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
