import json
from collections.abc import AsyncGenerator
from typing import Any, Optional

import jsonschema

from .errors import EditingError, ErrorAI, SuggestionError, WarningError
from .providers.api import ProviderAI


class ClientAI:
    __shell_command_jsonschema = {
        "type": "object",
        "properties": {"shell_command": {"type": "string"}},
        "required": ["shell_command"],
    }
    __warning_jsonschema = {
        "type": "object",
        "properties": {
            "dangerous_to_run": {"type": "boolean"},
            "dangerous_consequences": {"type": "string"},
        },
        "required": ["dangerous_to_run"],
    }

    def __init__(self, api: ProviderAI) -> None:
        self.__api = api

    async def suggest_shell_command(self, prompt: str) -> str:
        response = await self.__api.suggest_shell_command(prompt)
        shell_command = self.__validate_response(
            response, self.__shell_command_jsonschema, SuggestionError
        )["shell_command"]

        if shell_command == "":
            raise SuggestionError(
                f"Failed to suggest a shell command on request: {prompt}.\n"
                "The suggested shell command is empty."
            )
        else:
            return shell_command

    async def recognise_dangerous_command(
        self, shell_command: str
    ) -> tuple[bool, str]:
        response = await self.__api.recognise_dangerous_command(shell_command)
        evaluation = self.__validate_response(
            response, self.__warning_jsonschema, WarningError
        )

        is_dangerous = evaluation["dangerous_to_run"]
        dangerous_consequences = evaluation.get("dangerous_consequences", "")

        if not is_dangerous:
            return False, ""
        elif dangerous_consequences == "":
            raise WarningError(
                f"Expected dangerous consequences for {shell_command}, but got an empty string."
            )
        elif "\n" in dangerous_consequences:
            raise WarningError(
                f"Unexpected newline in dangerous consequences for {shell_command}: {dangerous_consequences}."
            )
        else:
            return True, dangerous_consequences

    async def get_explanation_of_shell_command(
        self, shell_command: str, *, model: Optional[str] = None
    ) -> str:
        return await self.__api.get_explanation_of_shell_command(
            shell_command, model=model
        )

    async def get_explanation_of_shell_command_by_chunks(
        self, stream: Any
    ) -> AsyncGenerator[str, None]:
        async for (
            chunk
        ) in self.__api.get_explanation_of_shell_command_by_chunks(stream):
            yield chunk

    async def edit_shell_command(self, shell_command: str, prompt: str) -> str:
        response = await self.__api.edit_shell_command(shell_command, prompt)
        shell_command = self.__validate_response(
            response, self.__shell_command_jsonschema, EditingError
        )["shell_command"]

        if shell_command == "":
            raise EditingError(
                f"Failed to edit {shell_command} on request: {prompt}.\n"
                "The edited shell command is empty."
            )
        else:
            return shell_command

    def __validate_response(
        self, s: str, schema: dict[str, Any], error: type[ErrorAI]
    ) -> dict[str, Any]:
        try:
            res = json.loads(s)
        except json.JSONDecodeError:
            raise error(f"LLM's response is not a valid JSON: {s}.")

        try:
            jsonschema.validate(res, schema)
        except jsonschema.ValidationError:
            raise error(
                f"LLM's response {res} doesn't match the expected JSON schema {schema}."
            )
        else:
            return res
