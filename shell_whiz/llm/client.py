import json
from typing import Any, Dict, Optional, Tuple

import jsonschema

from .errors import (
    EditingError,
    ExplanationError,
    TranslationError,
    WarningError,
)
from .providers.api import ProviderLLM


class ClientLLM:
    # These JSON schemas are only used to validate LLM responses
    __translation_jsonschema: Dict[str, Any] = {
        "type": "object",
        "properties": {"shell_command": {"type": "string"}},
        "required": ["shell_command"],
    }
    __dangerous_command_jsonschema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "dangerous_to_run": {"type": "boolean"},
            "dangerous_consequences": {"type": "string"},
        },
        "required": ["dangerous_to_run"],
    }
    __edited_shell_command_jsonschema: Dict[str, Any] = {
        "type": "object",
        "properties": {"edited_shell_command": {"type": "string"}},
        "required": ["edited_shell_command"],
    }

    def __init__(self, api: ProviderLLM) -> None:
        self.__api = api

    async def suggest_shell_command(self, prompt: str) -> str:
        shell_command = self.__validate_jsonschema(
            await self.__api.suggest_shell_command(prompt),
            self.__translation_jsonschema,
            TranslationError,
        )["shell_command"].strip()

        if shell_command == "":
            raise TranslationError("Extracted shell command is empty.")

        return shell_command

    async def recognize_dangerous_command(
        self, shell_command: str
    ) -> Tuple[bool, str]:
        dangerous_command_json = self.__validate_jsonschema(
            await self.__api.recognize_dangerous_command(shell_command),
            self.__dangerous_command_jsonschema,
            WarningError,
        )

        is_dangerous = dangerous_command_json["dangerous_to_run"]
        dangerous_consequences = dangerous_command_json.get(
            "dangerous_consequences", ""
        ).strip()

        if not is_dangerous:
            return False, ""
        elif dangerous_consequences == "":
            raise WarningError("Extracted dangerous consequences are empty.")
        elif "\n" in dangerous_consequences:
            raise WarningError(
                "Extracted dangerous consequences contain newlines."
            )
        else:
            return True, dangerous_consequences

    async def get_explanation_of_shell_command(
        self,
        shell_command: str,
        explain_using: Optional[str] = None,
        stream: bool = False,
    ) -> Any:
        return await self.__api.get_explanation_of_shell_command(
            shell_command, explain_using=explain_using, stream=stream
        )

    async def get_explanation_of_shell_command_by_chunks(
        self, stream=Any
    ) -> Any:
        is_first_chunk = True
        skip_initial_spaces = True
        async for chunk in self.__api.get_explanation_of_shell_command_by_chunks(  # type: ignore
            stream
        ):
            if chunk is None:
                break

            if skip_initial_spaces:
                chunk = chunk.lstrip()
                if chunk:
                    skip_initial_spaces = False
                else:
                    continue

            if is_first_chunk:
                if not chunk.startswith("*"):
                    raise ExplanationError("Explanation is not valid.")
                is_first_chunk = False

            yield chunk

    async def edit_shell_command(self, shell_command: str, prompt: str) -> str:
        edited_shell_command = self.__validate_jsonschema(
            await self.__api.edit_shell_command(shell_command, prompt),
            self.__edited_shell_command_jsonschema,
            EditingError,
        )["edited_shell_command"].strip()

        if edited_shell_command == "":
            raise EditingError("Edited shell command is empty.")

        return edited_shell_command

    def __validate_jsonschema(
        self, s: str, schema: Dict[str, Any], error: Any
    ) -> Dict[str, Any]:
        try:
            response_json = json.loads(s)
        except json.JSONDecodeError:
            raise error("Could not extract JSON.")

        try:
            jsonschema.validate(instance=response_json, schema=schema)
        except jsonschema.ValidationError:
            raise error("Generated JSON is not valid.")

        return response_json
