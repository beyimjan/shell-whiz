from pathlib import Path
from typing import Optional


class AskCLI:
    def __init__(
        self,
        openai_api_key: str,
        model: str,
        explain_using: str,
        preferences: str,
        openai_organization: Optional[str] = None,
    ):
        pass

    def __call__(
        self,
        prompt: list[str],
        explain_using: str,
        dont_warn: bool,
        dont_explain: bool,
        quiet: bool,
        shell: Optional[Path] = None,
        output: Optional[Path] = None,
    ):
        pass
