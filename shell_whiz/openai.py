import json
import os

import jsonschema
import openai
from jsonschema import validate

from shell_whiz.constants import DELIMITER
from shell_whiz.exceptions import (
    ShellWhizEditError,
    ShellWhizTranslationError,
    ShellWhizWarningError,
)
from shell_whiz.jsonschemas import (
    dangerous_command_json_schema,
    edited_shell_command_json_schema,
    translation_json_schema,
)


def get_my_preferences():
    return f"These are my preferences: {DELIMITER}\n{os.environ['SW_PREFERENCES']}\n{DELIMITER}"


def translate_nl_to_shell_command_openai(prompt):
    return openai.ChatCompletion.create(
        model=os.environ["SW_MODEL"],
        temperature=0.25,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": f"{get_my_preferences()}\n\n{prompt}",
            }
        ],
        functions=[
            {
                "name": "perform_task_in_command_line",
                "description": "Perform a task in the command line",
                "parameters": translation_json_schema,
            }
        ],
        function_call={"name": "perform_task_in_command_line"},
    ).choices[0]["message"]["function_call"]["arguments"]


def translate_nl_to_shell_command(prompt):
    translation = translate_nl_to_shell_command_openai(prompt)

    try:
        translation_json = json.loads(translation)
    except json.JSONDecodeError:
        raise ShellWhizTranslationError("Could not extract JSON.")

    try:
        validate(instance=translation_json, schema=translation_json_schema)
    except jsonschema.ValidationError:
        raise ShellWhizTranslationError("Generated JSON is not valid.")

    shell_command = translation_json.get("shell_command", "").strip()

    if shell_command == "":
        raise ShellWhizTranslationError("Extracted shell command is empty.")

    return shell_command


def recognize_dangerous_command_openai(shell_command):
    return openai.ChatCompletion.create(
        model=os.environ["SW_MODEL"],
        temperature=0,
        max_tokens=96,
        messages=[
            {
                "role": "user",
                "content": f"{get_my_preferences()}\n\nI want to run this command: {DELIMITER}\n{shell_command}\n{DELIMITER}",
            },
        ],
        functions=[
            {
                "name": "recognize_dangerous_command",
                "description": "Recognize a dangerous shell command. This function should be very low sensitive, only mark a command dangerous when it has very serious consequences.",
                "parameters": dangerous_command_json_schema,
            }
        ],
        function_call={"name": "recognize_dangerous_command"},
    ).choices[0]["message"]["function_call"]["arguments"]


def recognize_dangerous_command(shell_command):
    dangerous_command = recognize_dangerous_command_openai(shell_command)

    try:
        dangerous_command_json = json.loads(dangerous_command)
    except json.JSONDecodeError:
        raise ShellWhizWarningError("Could not extract JSON.")

    try:
        validate(
            instance=dangerous_command_json,
            schema=dangerous_command_json_schema,
        )
    except jsonschema.ValidationError:
        raise ShellWhizWarningError("Generated JSON is not valid.")

    is_dangerous = dangerous_command_json.get("dangerous_to_run", False)
    dangerous_consequences = dangerous_command_json.get(
        "dangerous_consequences", ""
    ).strip()

    if is_dangerous and dangerous_consequences == "":
        raise ShellWhizWarningError(
            "Extracted dangerous consequences are empty."
        )

    return is_dangerous, dangerous_consequences


def get_explanation_of_shell_command_openai(shell_command, explain_using_gpt_4):
    prompt = f'Break down each part of the command and explain it in a list format. Each line should follow the format of \'command piece\' followed by an explanation.\n\nFor example, if the command is `ls -l`, you would explain it as:\n* `ls` lists all files and directories in the current directory.\n  * `-l` displays files in a long listing format.\n\nFor `cat file | grep "foo"`, the explanation would be:\n* `cat file` outputs the content of the file.\n* `| grep "foo"` searches for the string "foo" in the output of the cat command.\n\n* Never explain basic command line concepts like pipes, variables, etc.\n* Keep explanations clear, simple, concise and elegant (under 7 words per line).\n* Use two spaces to indent for each nesting level in your list.\n\nIf you can\'t provide an explanation for a specific shell command or it\'s not a shell command, you should reply with an empty JSON object.\n\n{get_my_preferences()}\n\nShell command: {DELIMITER}\n{shell_command}\n{DELIMITER}'

    temperature = 0.1
    max_tokens = 512

    if explain_using_gpt_4:
        return (
            openai.ChatCompletion.create(
                model="gpt-4",
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            .choices[0]
            .message["content"]
        )
    else:
        return (
            openai.Completion.create(
                model="gpt-3.5-turbo-instruct",
                temperature=temperature,
                max_tokens=max_tokens,
                stop=["Shell"],
                prompt=prompt,
            )
            .choices[0]
            .text.strip()
        )


async def get_explanation_of_shell_command(shell_command, explain_using_gpt_4):
    return get_explanation_of_shell_command_openai(
        shell_command, explain_using_gpt_4
    )


def edit_shell_command_openai(shell_command, prompt):
    return openai.ChatCompletion.create(
        model=os.environ["SW_MODEL"],
        temperature=0.2,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": f"{shell_command}\n\nPrompt: {DELIMITER}\n{prompt}\n{DELIMITER}",
            },
        ],
        functions=[
            {
                "name": "edit_shell_command",
                "description": "Edit a shell command, according to the prompt",
                "parameters": edited_shell_command_json_schema,
            }
        ],
        function_call={"name": "edit_shell_command"},
    ).choices[0]["message"]["function_call"]["arguments"]


async def edit_shell_command(shell_command, prompt):
    edited_shell_command = edit_shell_command_openai(shell_command, prompt)

    try:
        edited_shell_command_json = json.loads(edited_shell_command)
    except json.JSONDecodeError:
        raise ShellWhizEditError("Could not extract JSON.")

    try:
        validate(
            instance=edited_shell_command_json,
            schema=edited_shell_command_json_schema,
        )
    except jsonschema.ValidationError:
        raise ShellWhizEditError("Generated JSON is not valid.")

    edited_shell_command = edited_shell_command_json.get(
        "edited_shell_command", ""
    ).strip()
    if edited_shell_command == "":
        raise ShellWhizEditError("Edited shell command is empty.")

    return edited_shell_command
