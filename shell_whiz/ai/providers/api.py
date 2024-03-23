from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Optional


class ProviderAI(ABC):
    """
    Helper class that defines the interface to implement Shell Whiz
    using different LLM providers (e.g. OpenAI, Anthropic, etc.).
    """

    @abstractmethod
    async def suggest_shell_command(self, prompt: str) -> str:
        """Suggests a shell command based on the given prompt. Returns JSON."""

    @abstractmethod
    async def recognise_dangerous_command(self, shell_command: str) -> str:
        """Checks if a shell command is dangerous to run. Returns JSON."""

    @abstractmethod
    async def get_explanation_of_shell_command(
        self, shell_command: str, *, model: Optional[str] = None
    ) -> Any:
        """Explains a shell command."""

    @abstractmethod
    async def get_explanation_of_shell_command_by_chunks(
        self, stream: Any
    ) -> AsyncGenerator[str, None]:
        """
        Helper function used to stream the result received by
        the `get_explanation_of_shell_command` function.
        """

        # Related issue: https://github.com/python/mypy/issues/5070
        if False:
            yield

    @abstractmethod
    async def edit_shell_command(self, shell_command: str, prompt: str) -> str:
        """Edits a shell command based on the given prompt. Returns JSON."""
