import asyncio
import sys
from typing import Annotated

import rich
import typer
from rich.live import Live
from rich.markdown import Markdown
from rich.status import Status

from shell_whiz.ai import ClientAI, ProviderOpenAI
from shell_whiz.config import Config, ConfigError


async def _run(ai: ClientAI, shell_command: str):
    with Status("Wait, Shell Whiz is thinking..."):
        stream = await ai.get_explanation_of_shell_command(shell_command)

    is_first_chunk = True
    explanation = ""
    with Live(auto_refresh=False) as live:
        async for chunk in ai.get_explanation_of_shell_command_by_chunks(
            stream
        ):
            if is_first_chunk:
                if chunk.startswith("-"):
                    rich.print(
                        "\n ================== [bold green]Explanation[/] =================="
                    )
                is_first_chunk = False
            explanation += chunk
            live.update(Markdown(explanation), refresh=True)


def explain(
    prompt: Annotated[str, typer.Argument(show_default=False)],
    preferences: Annotated[
        str,
        typer.Option(
            "-p", "--preferences", help="Preferences for the AI assistant."
        ),
    ] = "I use Bash on Linux",
    model: Annotated[
        str, typer.Option("-m", "--model", help="AI model to use.")
    ] = "gpt-3.5-turbo",
) -> None:
    """Explain a shell command"""

    try:
        config = Config()
    except ConfigError:
        rich.print(
            "[bold yellow]Error[/]: Please set your OpenAI API key via [bold green]sw config[/] and try again.",
            file=sys.stderr,
        )
        raise typer.Exit(1)

    asyncio.run(
        _run(
            ai=ClientAI(
                ProviderOpenAI(
                    api_key=config.openai_api_key,
                    organization=config.openai_org_id,
                    model=model,
                    preferences=preferences,
                )
            ),
            shell_command=prompt,
        )
    )
