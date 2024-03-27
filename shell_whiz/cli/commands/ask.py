import asyncio
import sys
from pathlib import Path
from typing import Annotated, Any, Optional

import questionary
import rich
import typer
from rich.live import Live
from rich.markdown import Markdown
from rich.status import Status

from shell_whiz.ai import (
    ClientAI,
    EditingError,
    ProviderOpenAI,
    SuggestionError,
    WarningError,
)
from shell_whiz.config import Config, ConfigError

from ..core.shell_command import ShellCommand


async def _explain_shell_command(*, ai: ClientAI, coro: Any) -> None:
    with Status("Wait, Shell Whiz is thinking..."):
        stream = await coro

    rich.print(
        " ================== [bold green]Explanation[/] =================="
    )

    is_first_chunk = True
    explanation = ""
    with Live(auto_refresh=False) as live:
        async for chunk in ai.get_explanation_of_shell_command_by_chunks(
            stream
        ):
            if is_first_chunk:
                if not chunk.startswith("-"):
                    print()
                is_first_chunk = False
            explanation += chunk
            live.update(Markdown(explanation), refresh=True)

    print()


async def _edit_shell_command(
    *, ai: ClientAI, shell_command: ShellCommand
) -> None:
    prompt = await questionary.text(
        "Enter your revision", validate=lambda x: x != ""
    ).unsafe_ask_async()

    print()
    try:
        with Status("Wait, Shell Whiz is thinking..."):
            shell_command.args = await ai.edit_shell_command(
                shell_command.args, prompt
            )
    except EditingError:
        rich.print(
            " Sorry, I couldn't edit the command. I left it unchanged.\n"
        )


async def _perform_selected_action(
    *,
    ai: ClientAI,
    shell_command: ShellCommand,
    actions: list[str],
    shell: Optional[Path] = None,
    output_file: Optional[Path] = None,
) -> None:
    while True:
        action = await questionary.select(
            "Select an action", actions
        ).unsafe_ask_async()

        if action == "Exit":
            raise typer.Exit(1)
        elif action == "Run this command":
            await shell_command.run(shell=shell, output_file=output_file)
        elif action == "Explain this command":
            print()
            await _explain_shell_command(
                ai=ai,
                coro=ai.get_explanation_of_shell_command(shell_command.args),
            )
        elif action == "Explain using GPT-4":
            print()
            await _explain_shell_command(
                ai=ai,
                coro=ai.get_explanation_of_shell_command(
                    shell_command.args, model="gpt-4-turbo-preview"
                ),
            )
        elif action == "Revise query":
            await _edit_shell_command(ai=ai, shell_command=shell_command)
            return
        elif action == "Edit manually":
            await shell_command.edit_manually()
            print()
            return


async def _run(
    *,
    ai: ClientAI,
    prompt: list[str],
    dont_warn: bool,
    dont_explain: bool,
    quiet: bool,
    actions: list[str],
    shell: Path | None,
    output_file: Path | None,
) -> None:
    try:
        with Status("Wait, Shell Whiz is thinking..."):
            shell_command = ShellCommand(
                await ai.suggest_shell_command(" ".join(prompt))
            )
    except SuggestionError:
        rich.print(
            "[bold yellow]Error[/]: Sorry, I don't know how to do this.",
            file=sys.stderr,
        )
        raise typer.Exit(1)
    else:
        print()

    while True:
        shell_command.display()

        if not dont_explain:
            explanation_task = asyncio.create_task(
                ai.get_explanation_of_shell_command(shell_command.args)
            )

        if not dont_warn:
            try:
                with Status("Wait, Shell Whiz is thinking..."):
                    (
                        shell_command.is_dangerous,
                        shell_command.dangerous_consequences,
                    ) = await ai.recognise_dangerous_command(
                        shell_command.args
                    )
            except WarningError:
                shell_command.is_dangerous = False

        if not dont_warn:
            shell_command.display_warning()

        if not dont_explain:
            await _explain_shell_command(ai=ai, coro=explanation_task)

        if quiet:
            break

        await _perform_selected_action(
            ai=ai,
            shell_command=shell_command,
            actions=actions,
            shell=shell,
            output_file=output_file,
        )


def _get_actions(*, dont_explain: bool, model: str) -> list[str]:
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

    if model.startswith("gpt-4"):
        actions.remove("Explain using GPT-4")

    return actions


def ask(
    prompt: Annotated[list[str], typer.Argument(show_default=False)],
    preferences: Annotated[
        str,
        typer.Option(
            "-p", "--preferences", help="Preferences for the AI assistant."
        ),
    ] = "I use Bash on Linux",
    model: Annotated[
        str, typer.Option("-m", "--model", help="AI model to use.")
    ] = "gpt-3.5-turbo",
    dont_warn: Annotated[
        bool, typer.Option(help="Skip the warning part.")
    ] = False,
    dont_explain: Annotated[
        bool,
        typer.Option(
            "-n",
            "--dont-explain/--no-dont-explain",
            help="Skip the explanation part.",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "-q", "--quiet/--no-quiet", help="Skip the interactive part."
        ),
    ] = False,
    shell: Annotated[
        Optional[Path],
        typer.Option(
            "-s",
            "--shell",
            help="Shell for executing the command. On Unix-like systems, this is usually /bin/sh. In Windows, it is usually cmd.exe.",
            dir_okay=False,
            show_default=False,
        ),
    ] = None,
    output_file: Annotated[
        Optional[Path],
        typer.Option(
            "-o",
            "--output",
            help="Instead of running the command, specify the output file for post-processing.",
            dir_okay=False,
            writable=True,
            show_default=False,
        ),
    ] = None,
) -> None:
    """Get assistance from AI"""

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
            prompt=prompt,
            dont_warn=dont_warn,
            dont_explain=dont_explain,
            quiet=quiet,
            actions=_get_actions(dont_explain=dont_explain, model=model),
            shell=shell,
            output_file=output_file,
        )
    )
