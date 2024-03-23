from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Optional

import yaml
from openai import AsyncOpenAI

from .api import ProviderAI


class ProviderOpenAI(ProviderAI):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        preferences: str,
        organization: Optional[str] = None,
    ) -> None:
        self.__client = AsyncOpenAI(api_key=api_key, organization=organization)

        self.__model = model

        self.__preferences = (
            f"These are my preferences: ####\n{preferences}\n####"
        )

        self.__messages = [
            {
                "role": "system",
                "content": f"You are Shell Whiz, an AI assistant for the command line.\n\nUnless I specify otherwise in my preferences below, you typically provide expert-level responses.\n\n{self.__preferences}",
            }
        ]

    async def suggest_shell_command(self, prompt: str) -> str:
        """Suggests a shell command based on the given prompt. Returns JSON."""

        message = await self.__continue_conversation(
            prompt,
            **yaml.safe_load(
                (
                    Path(__file__).parent.parent
                    / "prompts"
                    / "suggest_shell_command.yml"
                ).read_text()
            ),
        )

        return message.function_call.arguments

    async def recognise_dangerous_command(self, shell_command: str) -> str:
        """Checks if a shell command is dangerous to run. Returns JSON."""

        message = await self.__continue_conversation(
            f"{shell_command}\n\nIs this command safe to execute?",
            **yaml.safe_load(
                (
                    Path(__file__).parent.parent
                    / "prompts"
                    / "recognise_dangerous_command.yml"
                ).read_text()
            ),
        )

        return message.function_call.arguments

    async def get_explanation_of_shell_command(
        self, shell_command: str, *, model: Optional[str] = None
    ) -> Any:
        """Explains a shell command."""

        prompt = yaml.safe_load(
            (
                Path(__file__).parent.parent
                / "prompts"
                / "explain_shell_command.yml"
            ).read_text()
        )
        prompt["messages"][0]["content"] = prompt["messages"][0][
            "content"
        ].format(preferences=self.__preferences)
        prompt["messages"].append({"role": "user", "content": shell_command})

        stream = await self.__create_chat_completion(
            model=model or self.__model, stream=True, **prompt
        )

        return stream

    async def get_explanation_of_shell_command_by_chunks(
        self, stream: Any
    ) -> AsyncGenerator[str, None]:
        """
        Helper function used to stream the result received by
        the `get_explanation_of_shell_command` function.
        """

        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    async def edit_shell_command(self, shell_command: str, prompt: str) -> str:
        """Edits a shell command based on the given prompt. Returns JSON."""

        message = await self.__continue_conversation(
            f"{shell_command}\n\n{prompt}",
            **yaml.safe_load(
                (
                    Path(__file__).parent.parent
                    / "prompts"
                    / "edit_shell_command.yml"
                ).read_text()
            ),
        )

        return message.function_call.arguments

    async def __continue_conversation(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        function_call: Optional[dict[str, str]] = None,
        functions: Optional[list[dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict[str, str]] = None,
        temperature: Optional[float] = None,
    ) -> Any:
        self.__messages.append({"role": "user", "content": prompt})

        message = await self.__create_chat_completion(
            messages=self.__messages,
            model=model or self.__model,
            function_call=function_call,
            functions=functions,
            max_tokens=max_tokens,
            response_format=response_format,
            temperature=temperature,
        )

        self.__messages.append(message)

        return message

    async def __create_chat_completion(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        function_call: Optional[dict[str, str]] = None,
        functions: Optional[list[dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict[str, str]] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
    ) -> Any:
        response = await self.__client.chat.completions.create(  # type: ignore
            messages=messages,
            model=model,
            function_call=function_call,
            functions=functions,
            max_tokens=max_tokens,
            response_format=response_format,
            stream=stream,
            temperature=temperature,
        )

        if stream:
            return response
        else:
            return response.choices[0].message
