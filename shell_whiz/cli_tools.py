import sys

import rich


def pretty_log_error(error, prefix="[bold yellow]Error[/]"):
    rich.print(f"{prefix}: {error}", file=sys.stderr)
