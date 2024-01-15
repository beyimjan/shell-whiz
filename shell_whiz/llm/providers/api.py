from abc import ABC, abstractmethod
from typing import Any, Optional


class ProviderLLM(ABC):
    @abstractmethod
    async def suggest_shell_command(self, prompt: str) -> str:
        pass

    @abstractmethod
    async def recognize_dangerous_command(self, shell_command: str) -> str:
        pass

    @abstractmethod
    async def get_explanation_of_shell_command(
        self,
        shell_command: str,
        stream: bool,
        explain_using: Optional[str] = None,
    ) -> Any:
        pass

    @abstractmethod
    async def get_explanation_of_shell_command_by_chunks(
        self, stream: Any
    ) -> Any:
        pass

    @abstractmethod
    async def edit_shell_command(self, shell_command: str, prompt: str) -> str:
        pass
