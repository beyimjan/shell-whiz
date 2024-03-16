import asyncio
import os
import subprocess
from pathlib import Path
from typing import Optional

import questionary
import rich
import typer
from rich.live import Live
from rich.markdown import Markdown
from rich.status import Status

from shell_whiz.llm import (
    ClientLLM,
    ExplanationError,
    ProviderOpenAI,
    SuggestionError,
)


class _CMD:
    shell_command: str
    is_dangerous: bool = False
    dangerous_consequences: str | None = None

    def __init__(self, shell_command: str):
        self.shell_command = shell_command

    def cat(self):
        rich.print(
            "\n ==================== [bold green]Command[/] ====================\n"
        )
        print(
            " " + " ".join(self.shell_command.splitlines(keepends=True)) + "\n"
        )

    def warn(self):
        if self.is_dangerous and self.dangerous_consequences:
            rich.print(
                " [bold red]Warning[/]: [bold yellow]{0}[/]\n".format(
                    self.dangerous_consequences
                )
            )

    async def explain(self, stream) -> None:
        rich.print(
            " ================== [bold green]Explanation[/] =================="
        )

        with Live(auto_refresh=False) as live:
            explanation = ""
            async for chunk in stream:
                explanation += chunk
                live.update(Markdown(explanation), refresh=True)

        print()

    async def run(self, shell, output) -> None:
        if self.is_dangerous:
            if not await questionary.confirm(
                "Are you sure you want to run this command?"
            ).unsafe_ask_async():
                return

        if output:
            try:
                with open(output, "w", newline="\n") as f:
                    f.write(self.shell_command)
            except os.error:
                rich.print("Couldn't write to output file.")
                raise typer.Exit(1)
        else:
            subprocess.run(self.shell_command, executable=shell, shell=True)

        raise typer.Exit()

    async def edit(self) -> None:
        res = (
            await questionary.text(
                "Edit command",
                default=self.shell_command,
                multiline="\n" in self.shell_command,
            ).unsafe_ask_async()
        ).strip()

        if res not in ("", self.shell_command):
            self.shell_command = res


class AskCLI:
    def __init__(
        self,
        openai_api_key: str,
        model: str,
        explain_using: str,
        preferences: str,
        openai_org_id: Optional[str] = None,
    ):
        self.__llm = ClientLLM(
            ProviderOpenAI(
                api_key=openai_api_key,
                model=model,
                explain_using=explain_using,
                preferences=preferences,
                organization=openai_org_id,
            )
        )

    async def __call__(
        self,
        prompt: list[str],
        explain_using: str,
        dont_warn: bool,
        dont_explain: bool,
        quiet: bool,
        shell: Optional[Path] = None,
        output: Optional[Path] = None,
    ):
        try:
            with Status("Wait, Shell Whiz is thinking..."):
                self.__cmd = _CMD(
                    await self.__llm.suggest_shell_command(" ".join(prompt))
                )
        except SuggestionError:
            rich.print(
                "[bold yellow]Error[/]: Sorry, I don't know how to do this."
            )
            raise typer.Exit(1)

        actions = AskCLI.__get_actions(explain_using, dont_explain)
        while True:
            if not dont_explain:
                self.__cmd.cat()
                explanation_task = asyncio.create_task(
                    self.__llm.get_explanation_of_shell_command(
                        self.__cmd.shell_command
                    )
                )

            if dont_warn:
                self.__cmd.is_dangerous = False
            else:
                with Status(
                    "Shell Whiz is checking the command for danger..."
                ):
                    (
                        self.__cmd.is_dangerous,
                        self.__cmd.dangerous_consequences,
                    ) = await self.__llm.recognise_dangerous_command(
                        self.__cmd.shell_command
                    )

            if dont_explain:
                self.__cmd.cat()

            if not dont_warn:
                self.__cmd.warn()

            if not dont_explain:
                await self.__explain(await explanation_task)

            if quiet:
                break

            await self.__perform_selected_action(actions, shell, output)

    async def __explain(self, stream):
        try:
            await self.__cmd.explain(
                self.__llm.get_explanation_of_shell_command_by_chunks(stream)
            )
        except ExplanationError:
            rich.print(" Sorry, I don't know how to explain this command.\n")

    async def __perform_selected_action(self, actions, shell, output):
        while True:
            action = await questionary.select(
                "Select an action", choices=actions
            ).unsafe_ask_async()

            if action == "Exit":
                raise typer.Exit(1)
            elif action == "Run this command":
                await self.__cmd.run(shell, output)
            elif action == "Explain this command":
                await self.__explain(
                    await self.__llm.get_explanation_of_shell_command(
                        self.__cmd.shell_command
                    )
                )
            elif action == "Explain using GPT-4 Turbo":
                print()
                await self.__explain(
                    await self.__llm.get_explanation_of_shell_command(
                        self.__cmd.shell_command,
                        explain_using="gpt-4-turbo-preview",
                    )
                )
            elif action == "Revise query":
                # await cmd.revise(self.__llm.edit_shell_command)
                # break
                pass
            elif action == "Edit manually":
                await self.__cmd.edit()
                break

    @staticmethod
    def __get_actions(explain_using: str, dont_explain: bool) -> list[str]:
        actions = [
            "Run this command",
            "Explain this command",
            "Explain using GPT-4 Turbo",
            "Revise query",
            "Edit manually",
            "Exit",
        ]

        if not dont_explain:
            actions.remove("Explain this command")

        if explain_using.startswith("gpt-4-turbo"):
            actions.remove("Explain using GPT-4 Turbo")

        return actions
