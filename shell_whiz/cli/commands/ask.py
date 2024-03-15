from pathlib import Path
from typing import Optional

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
        shell_command = await self.__llm.suggest_shell_command(
            " ".join(prompt)
        )
        print(shell_command)

        (
            is_dangerous,
            dangerous_consequences,
        ) = await self.__llm.recognise_dangerous_command(shell_command)
        print(f"{is_dangerous=}, {dangerous_consequences=}")
