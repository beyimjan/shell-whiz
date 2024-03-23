import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

import questionary
import rich
import typer


class ShellCommand:
    args: str
    is_dangerous: bool = False
    dangerous_consequences: str = ""

    def __init__(self, args: str) -> None:
        self.args = args

    async def edit_manually(self) -> None:
        shell_command = await questionary.text(
            "Edit command", default=self.args, multiline="\n" in self.args
        ).unsafe_ask_async()

        if shell_command not in ("", self.args):
            self.args = shell_command

    def display(self) -> None:
        rich.print(
            " ==================== [bold green]Command[/] ====================\n"
        )
        print(" " + " ".join(self.args.splitlines(keepends=True)) + "\n")

    def display_warning(self) -> None:
        if self.is_dangerous and self.dangerous_consequences:
            rich.print(
                " [bold red]Warning[/]: [bold yellow]{0}[/]\n".format(
                    self.dangerous_consequences
                )
            )

    async def run(
        self, *, shell: Path | None, output_file: Path | None
    ) -> NoReturn:
        if self.is_dangerous:
            if not await questionary.confirm(
                "Are you sure you want to run this command?"
            ).unsafe_ask_async():
                raise typer.Exit(1)

        if output_file:
            try:
                with open(output_file, mode="w", newline="\n") as f:
                    f.write(self.args)
            except os.error:
                rich.print(
                    "[bold yellow]Error[/]: Failed to write to the output file.",
                    file=sys.stderr,
                )
                raise typer.Exit(1)
        else:
            subprocess.run(self.args, executable=shell, shell=True)

        raise typer.Exit()
