import json
from typing import Any

import jsonschema

from shell_whiz.llm.errors import ErrorLLM, SuggestionError, WarningError
from shell_whiz.llm.providers.api import ProviderLLM


class ClientLLM:
    __shell_command_jsonschema = {
        "type": "object",
        "properties": {"shell_command": {"type": "string"}},
        "required": ["shell_command"],
    }
    __execution_risk_jsonschema = {
        "type": "object",
        "properties": {
            "dangerous_to_run": {"type": "boolean"},
            "dangerous_consequences": {"type": "string"},
        },
        "required": ["dangerous_to_run"],
    }

    def __init__(self, api: ProviderLLM) -> None:
        self.__api = api

    async def suggest_shell_command(self, prompt: str) -> str:
        response = await self.__api.suggest_shell_command(prompt)

        shell_command = self.__validate_response(
            response, self.__shell_command_jsonschema, SuggestionError
        )["shell_command"]

        if shell_command == "":
            raise SuggestionError("Suggested shell command is empty.")
        else:
            return shell_command

    async def recognise_dangerous_command(
        self, shell_command: str
    ) -> list[bool, str]:
        response = await self.__api.recognise_dangerous_command(shell_command)

        evaluation = self.__validate_response(
            response, self.__execution_risk_jsonschema, WarningError
        )

        is_dangerous = evaluation["dangerous_to_run"]
        dangerous_consequences = evaluation.get(
            "dangerous_consequences", ""
        ).strip()

        if not is_dangerous:
            return False, ""
        elif dangerous_consequences == "":
            raise WarningError("Dangerous consequences are empty.")
        elif "\n" in dangerous_consequences:
            raise WarningError(
                "Dangerous consequences contain a newline character."
            )
        else:
            return True, dangerous_consequences

    def __validate_response(
        self, s: str, schema: dict[str, Any], error: type[ErrorLLM]
    ) -> dict[str, Any]:
        try:
            res = json.loads(s)
        except json.JSONDecodeError:
            raise error("LLM's response is not valid JSON.")

        try:
            jsonschema.validate(instance=res, schema=schema)
        except jsonschema.ValidationError:
            raise error(
                "LLM's response didn't match the expected JSON schema."
            )
        else:
            return res
