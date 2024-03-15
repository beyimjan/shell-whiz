from pathlib import Path
from typing import Optional

import rich
from rich.live import Live
from rich.markdown import Markdown
from rich.status import Status

from shell_whiz.llm import ClientLLM, ProviderOpenAI


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
        with Status("Wait, Shell Whiz is thinking..."):
            shell_command = await self.__llm.suggest_shell_command(
                " ".join(prompt)
            )

        rich.print(
            "\n ==================== [bold green]Command[/] ====================\n"
        )
        print(" " + " ".join(shell_command.splitlines(keepends=True)) + "\n")

        with Status("Shell Whiz is checking the command for danger..."):
            (
                is_dangerous,
                dangerous_consequences,
            ) = await self.__llm.recognise_dangerous_command(shell_command)

        if is_dangerous:
            rich.print(
                " [bold red]Warning[/]: [bold yellow]{0}[/]\n".format(
                    dangerous_consequences
                )
            )

        rich.print(
            " ================== [bold green]Explanation[/] =================="
        )

        with Live(auto_refresh=False) as live:
            explanation = ""
            async for chunk in self.__llm.get_explanation_of_shell_command_by_chunks(
                await self.__llm.get_explanation_of_shell_command(
                    shell_command
                )
            ):
                explanation += chunk
                live.update(Markdown(explanation), refresh=True)
