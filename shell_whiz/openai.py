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


# https://platform.openai.com/playground/p/FdYUdbAGL530Lfh5VesLlVD8?model=gpt-3.5-turbo
def translate_nl_to_shell_command_openai(prompt):
    return (
        openai.ChatCompletion.create(
            model=os.environ["SW_MODEL"],
            temperature=0.25,
            max_tokens=256,
            messages=[
                {
                    "role": "system",
                    "content": f"I want you to act as an artificial intelligence assistant specifically for command-line inquiries. Whenever I pose a problem, your responsibility is to provide a ready-to-run shell command that could solve it. The response must be formatted in JSON where the key is shell_command. If the query falls outside of this designated scope, you should reply with an empty JSON object.\n\nQueries will be separated by {DELIMITER} characters.\n\n## PERSONALIZATION\nIn addition, I would like to set my default shell and add my preferences to your functions. This should reflect in your responses, taking into account my usually used commands and preferred shell environments.\n\n```\nI usually use Bash on Linux\n```\n\n## END",
                },
                {
                    "role": "user",
                    "content": f"{DELIMITER}\n{prompt}\n{DELIMITER}",
                },
            ],
        )
        .choices[0]
        .message["content"]
    )


def translate_nl_to_shell_command(prompt):
    translation_json_schema = {
        "type": "object",
        "properties": {"shell_command": {"type": "string"}},
        "required": ["shell_command"],
    }

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


# https://platform.openai.com/playground/p/H3HMz4fgnQQUTT6PI17qDtzQ?model=gpt-3.5-turbo
def recognize_dangerous_command_openai(shell_command):
    return (
        openai.ChatCompletion.create(
            model=os.environ["SW_MODEL"],
            temperature=0,
            max_tokens=96,
            messages=[
                {
                    "role": "user",
                    "content": f'I want you to act as a warning system for dangerous shell commands. I will provide you with the shell command and your job is to take it and reply back with a JSON object. If you deem the command dangerous, please set the "dangerous_to_run" key to "true". If you believe it won\'t pose any imminent danger, set "dangerous_to_run" key to "false". Optionally, you can also include the "dangerous_consequences" key followed by a brief explanation, no more than 12 words, which describes the potential side effects of running the command. This function should be very low sensitive, only mark a command dangerous when it has very serious consequences.\n\nCommand to execute: ####\n{shell_command}\n####',
                }
            ],
        )
        .choices[0]
        .message["content"]
    )


def recognize_dangerous_command(shell_command):
    dangerous_command_json_schema = {
        "type": "object",
        "properties": {
            "dangerous_to_run": {"type": "boolean"},
            "dangerous_consequences": {"type": "string"},
        },
        "required": ["dangerous_to_run"],
    }

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


# https://platform.openai.com/playground/p/SXqnxM1MPDvywzFUlAjvYNlm?model=gpt-3.5-turbo
def get_explanation_of_shell_command_openai(shell_command, explain_using_gpt_4):
    if explain_using_gpt_4:
        model = "gpt-4"
    else:
        model = os.environ["SW_MODEL"]

    return (
        openai.ChatCompletion.create(
            model=model,
            temperature=0.1,
            max_tokens=512,
            messages=[
                {
                    "role": "system",
                    "content": "I want you to act as a shell command explainer. Break down each part of the command and explain it in a list format. Use nested bullets for arguments and increase the level of nesting for clarity. Each line should follow the format of 'command piece' followed by an explanation.\n\nFor example, if the command is `ls -l`, you would explain it as:\n* `ls` lists all files and directories in the current directory.\n  * `-l` displays files in a long listing format.\n\nFor `cat file | grep \"foo\"`, the explanation would be:\n* `cat file` outputs the content of the file.\n* `| grep \"foo\"` searches for the string \"foo\" in the output of the cat command.\n\n* Don't repeat arguments in the text.\n* Never explain basic command line concepts like pipes, variables, etc.\n* Increase nesting levels when explaining arguments.\n* Place code segments in backticks.\n* Keep explanations clear and concise (under 7 words per line).\n* Use two spaces to indent for each nesting level in your list.\n\nIf you can't provide an explanation for a specific shell command or it's not a shell command, simply answer 'N'.",
                },
                {
                    "role": "user",
                    "content": f"{DELIMITER}\n{shell_command}\n{DELIMITER}",
                },
            ],
        )
        .choices[0]
        .message["content"]
    )


async def get_explanation_of_shell_command(shell_command, explain_using_gpt_4):
    return get_explanation_of_shell_command_openai(
        shell_command, explain_using_gpt_4
    )


# https://platform.openai.com/playground/p/9GjFtlveQhpN1SBciahtNAQf?model=gpt-3.5-turbo
def edit_shell_command_openai(shell_command, prompt):
    return (
        openai.ChatCompletion.create(
            model=os.environ["SW_MODEL"],
            messages=[
                {
                    "role": "user",
                    "content": f"Shell command to edit: ####\n{shell_command}\n####\n\nUser prompt to edit this shell command: ####\n{prompt}\n####\n\nEdit the command according to the user's prompt and generate a JSON object with one key \"edited_shell_command\". If you can't edit the command as requested, output an empty JSON object.\n\nOnly generate JSON to make your output machine readable.",
                }
            ],
            temperature=0.2,
            max_tokens=256,
        )
        .choices[0]
        .message["content"]
    )


async def edit_shell_command(shell_command, prompt):
    edited_sc_json_schema = {
        "type": "object",
        "properties": {"edited_shell_command": {"type": "string"}},
        "required": ["edited_shell_command"],
    }

    edited_sc = edit_shell_command_openai(shell_command, prompt)

    try:
        edited_sc_json = json.loads(edited_sc)
    except json.JSONDecodeError:
        raise ShellWhizEditError("Could not extract JSON.")

    try:
        validate(instance=edited_sc_json, schema=edited_sc_json_schema)
    except jsonschema.ValidationError:
        raise ShellWhizEditError("Generated JSON is not valid.")

    edited_sc = edited_sc_json["edited_shell_command"]
    if edited_sc == "":
        raise ShellWhizEditError("Edited shell command is empty.")

    return edited_sc
