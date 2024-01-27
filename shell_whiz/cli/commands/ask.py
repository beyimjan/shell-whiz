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

from shell_whiz.config import ConfigData
from shell_whiz.llm import ClientLLM, ProviderOpenAI
from shell_whiz.llm.errors import (
    EditingError,
    ExplanationError,
    TranslationError,
    WarningError,
)


class _CMD:
    def __init__(
        self,
        shell_command: str,
        is_dangerous: bool = False,
        dangerous_consequences: str = "",
    ) -> None:
        self.shell_command = shell_command
        self.is_dangerous = is_dangerous
        self.dangerous_consequences = dangerous_consequences

    @classmethod
    async def init(cls, prompt: str, shell_whiz) -> Any:
        try:
            with Status("Wait, Shell Whiz is thinking..."):
                return cls(await shell_whiz(prompt))
        except TranslationError:
            rich.print("Sorry, I don't know how to do this.")
            sys.exit(1)

    def cat(self) -> None:
        rich.print(
            "\n ==================== [bold green]Command[/] ====================\n"
        )
        print(
            " " + " ".join(self.shell_command.splitlines(keepends=True)) + "\n"
        )

    async def safety_check(self, shell_whiz) -> None:
        try:
            with Status("Shell Whiz is checking the command for danger..."):
                (
                    self.is_dangerous,
                    self.dangerous_consequences,
                ) = await shell_whiz(self.shell_command)
        except WarningError:
            self.__is_dangerous = False

    async def explain(self, shell_whiz) -> None:
        rich.print(
            " ================== [bold green]Explanation[/] =================="
        )

        try:
            with Live(auto_refresh=False) as live:
                explanation = ""
                async for explanation_chunk in shell_whiz:
                    explanation += explanation_chunk
                    live.update(Markdown(explanation), refresh=True)
        except ExplanationError:
            rich.print(" Sorry, I don't know how to explain this command.")

        print()

    async def run(self, shell: Any, output: Any) -> None:
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
                sys.exit(2)
        else:
            subprocess.run(self.shell_command, executable=shell, shell=True)

        sys.exit()

    async def revise(self, shell_whiz) -> None:
        prompt = (
            await questionary.text("Enter your revision").unsafe_ask_async()
        ).strip()

        if prompt == "":
            return

        try:
            with Status("Wait, Shell Whiz is thinking..."):
                self.shell_command = await shell_whiz(
                    self.shell_command, prompt
                )
        except EditingError:
            rich.print(
                "\n  Sorry, I couldn't edit the command. I left it unchanged."
            )

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
    def __init__(self, config: ConfigData, model, preferences) -> None:
        self.__llm = ClientLLM(
            ProviderOpenAI(config["OPENAI_API_KEY"], model, preferences)
        )

    async def __call__(
        self,
        prompt,
        explain_using,
        dont_explain,
        dont_warn,
        quiet,
        shell,
        output,
    ) -> None:
        actions = AskCLI.__make_actions(explain_using, dont_explain)

        cmd = await _CMD.init(
            prompt, shell_whiz=self.__llm.suggest_shell_command
        )

        while True:
            await self.__warn_and_explain(cmd, dont_warn, dont_explain)
            if quiet:
                sys.exit(2)

            await self.__perform_selected_action(cmd, actions, shell, output)

    async def __warn_and_explain(
        self, cmd: _CMD, dont_warn, dont_explain
    ) -> None:
        if not dont_explain:
            cmd.cat()
            explanation_task = asyncio.create_task(
                self.__llm.get_explanation_of_shell_command(
                    cmd.shell_command, True
                )
            )

        if dont_warn:
            cmd.is_dangerous = False
        else:
            await cmd.safety_check(self.__llm.recognize_dangerous_command)

        if dont_explain:
            cmd.cat()

        if not dont_warn and cmd.is_dangerous:
            rich.print(
                " [bold red]Warning[/]: [bold yellow]{0}[/]\n".format(
                    cmd.dangerous_consequences
                )
            )

        if not dont_explain:
            await cmd.explain(
                self.__llm.get_explanation_of_shell_command_by_chunks(
                    await explanation_task
                )
            )

    async def __perform_selected_action(
        self, cmd: _CMD, actions, shell, output
    ) -> None:
        while True:
            action = await questionary.select(
                "Select an action", choices=actions
            ).unsafe_ask_async()

            if action == "Exit":
                sys.exit(2)
            elif action == "Run this command":
                await cmd.run(shell, output)
            elif action == "Explain this command":
                await cmd.explain(
                    self.__llm.get_explanation_of_shell_command_by_chunks(
                        await self.__llm.get_explanation_of_shell_command(
                            cmd.shell_command, True
                        )
                    )
                )
            elif action == "Explain using GPT-4 Turbo [BETA]":
                print()
                await cmd.explain(
                    self.__llm.get_explanation_of_shell_command_by_chunks(
                        await self.__llm.get_explanation_of_shell_command(
                            cmd.shell_command,
                            True,
                            explain_using="gpt-4-turbo-preview",
                        )
                    )
                )
            elif action == "Explain using GPT-4":
                print()
                await cmd.explain(
                    self.__llm.get_explanation_of_shell_command_by_chunks(
                        await self.__llm.get_explanation_of_shell_command(
                            cmd.shell_command, True, explain_using="gpt-4"
                        )
                    )
                )
            elif action == "Revise query":
                await cmd.revise(self.__llm.edit_shell_command)
                break
            elif action == "Edit manually":
                await cmd.edit()
                break

    @staticmethod
    def __make_actions(explain_using, dont_explain) -> list[str]:
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

        if explain_using == "gpt-4-turbo-preview":
            actions.remove("Explain using GPT-4 Turbo [BETA]")
        elif explain_using == "gpt-4":
            actions.remove("Explain using GPT-4")

        return actions
