from typing import Any, Dict, Optional

from openai import AsyncOpenAI

from .api import ProviderLLM


class ClientOpenAI(ProviderLLM):
    # These JSON schemas are part of the prompts
    __translation_jsonschema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "shell_command": {
                "type": "string",
                "description": "Shell command to perform the task. You just get things done, rather than trying to explain. Leave blank if it is not possible to perform the task in the command line.",
            }
        },
        "required": ["shell_command"],
    }
    __dangerous_command_jsonschema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "dangerous_to_run": {"type": "boolean"},
            "dangerous_consequences": {
                "type": "string",
                "description": "Brief explanation of the potential side effects of running the command. Less than 12 words.",
            },
        },
        "required": ["dangerous_to_run"],
    }
    __edited_shell_command_jsonschema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "edited_shell_command": {
                "type": "string",
                "description": "Edited shell command, leave blank if you couldn't edit it",
            }
        },
        "required": ["edited_shell_command"],
    }

    def __init__(
        self,
        api_key: str,
        model: str,
        preferences: str,
        explain_using: Optional[str] = None,
    ) -> None:
        self.__client = AsyncOpenAI(api_key=api_key)
        self.__model = model
        self.__explain_using = explain_using or model
        self.__preferences = (
            f"These are my preferences: ####\n{preferences}\n####"
        )

    async def suggest_shell_command(self, prompt: str) -> str:
        response = await self.__client.chat.completions.create(
            model=self.__model,
            temperature=0.25,
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": f"{self.__preferences}\n\n{prompt}",
                }
            ],
            functions=[
                {
                    "name": "perform_task_in_command_line",
                    "description": "Perform a task in the command line",
                    "parameters": self.__translation_jsonschema,
                }
            ],
            function_call={"name": "perform_task_in_command_line"},
        )
        return response.choices[0].message.function_call.arguments  # type: ignore

    async def recognize_dangerous_command(self, shell_command: str) -> str:
        response = await self.__client.chat.completions.create(
            model=self.__model,
            temperature=0,
            max_tokens=96,
            messages=[
                {
                    "role": "user",
                    "content": f"{self.__preferences}\n\nI want to run this command: ####\n{shell_command}\n####",
                }
            ],
            functions=[
                {
                    "name": "recognize_dangerous_command",
                    "description": "Recognize a dangerous shell command. This function should be very low sensitive, only mark a command dangerous when it has very serious consequences.",
                    "parameters": self.__dangerous_command_jsonschema,
                }
            ],
            function_call={"name": "recognize_dangerous_command"},
        )
        return response.choices[0].message.function_call.arguments  # type: ignore

    async def get_explanation_of_shell_command(
        self,
        shell_command: str,
        explain_using: Optional[str] = None,
        stream: bool = False,
    ) -> Any:
        return await self.__client.chat.completions.create(
            model=explain_using or self.__explain_using,
            temperature=0.1,
            max_tokens=512,
            stream=stream,
            messages=[
                {
                    "role": "user",
                    "content": f'Break down the command into parts and explain it in a **list** format. Each line should follow the format "part of the command", with an explanation afterward. ALWAYS start your answer with an asterisk when you start explaining a shell command. ONLY AND ONLY IF you are unable to explain the command or if it is not a shell command, reply with an empty JSON.\n\nFor example, if the command is `ls -l`, you would explain it as:\n* `ls` lists directory contents.\n  * `-l` displays in long format.\n\nFor `cat file | grep "foo"`, the explanation would be:\n* `cat file` reads the content of `file`.\n* `| grep "foo"` filters lines containing "foo".\n\n* Never explain basic command line concepts like pipes, variables, etc.\n* Keep explanations clear, simple, concise and elegant (under 7 words per line).\n* Use two spaces to indent for each nesting level in your list.\n\n{self.__preferences}\n\nShell command: ####\n{shell_command}\n####',
                }
            ],
        )

    async def get_explanation_of_shell_command_by_chunks(
        self, stream: Any
    ) -> Any:
        async for chunk in stream:
            yield chunk.choices[0].delta.content

    async def edit_shell_command(self, shell_command: str, prompt: str) -> str:
        response = await self.__client.chat.completions.create(
            model=self.__model,
            temperature=0.2,
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": f"{shell_command}\n\nPrompt: ####\n{prompt}\n####",
                }
            ],
            functions=[
                {
                    "name": "edit_shell_command",
                    "description": "Edit a shell command, according to the prompt",
                    "parameters": self.__edited_shell_command_jsonschema,
                }
            ],
            function_call={"name": "edit_shell_command"},
        )
        return response.choices[0].message.function_call.arguments  # type: ignore