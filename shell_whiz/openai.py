import json
from json import JSONDecodeError

import openai
from yaspin import yaspin

from .exceptions import ShellWhizTranslationError

DELIMITER = "####"
SHELL = "Bash"

NL_TO_SHELL_COMMAND_PMT = """You are a {SHELL} command translator. Your role is to translate natural language into a {SHELL} command. Think that all necessary programs are installed.

Provide only a ready-to-execute command. Do not write any explanation.

Queries will be separated by {DELIMITER} characters."""


def extract_shell_command_from_text(haystack):
    extracted_json = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=0,
        max_tokens=256,
        messages=[
            {
                "role": "system",
                "content": 'Extract JSON from user messages with a single key "shell_command". Only generate JSON to make your output machine readable.',
            },
            {
                "role": "user",
                "content": f"{DELIMITER}\n{haystack}\n{DELIMITER}",
            },
        ],
    )

    try:
        extracted_json = json.loads(
            extracted_json.choices[0].message["content"]
        )
    except JSONDecodeError:
        raise ShellWhizTranslationError("Could not extract JSON.")

    if not isinstance(extracted_json, dict):
        raise ShellWhizTranslationError("Generated JSON is not valid.")

    extracted_shell_command = extracted_json.get("shell_command", None)
    if extracted_shell_command is None:
        raise ShellWhizTranslationError(
            "Generated JSON doesn't have 'shell_command' key."
        )
    elif not isinstance(extracted_shell_command, str):
        raise ShellWhizTranslationError(
            "Extracted shell command is not a str."
        )

    extracted_shell_command = extracted_shell_command.strip()
    if extracted_shell_command == "":
        raise ShellWhizTranslationError("Extracted shell command is empty.")

    return extracted_shell_command


@yaspin(text="Wait, Shell Whiz is thinking", color="green")
def translate_natural_language_to_shell_command(query):
    translation = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=0.35,
        max_tokens=256,
        messages=[
            {
                "role": "system",
                "content": NL_TO_SHELL_COMMAND_PMT.format(
                    SHELL=SHELL, DELIMITER=DELIMITER
                ),
            },
            {
                "role": "user",
                "content": f"{DELIMITER}\n{query}\n{DELIMITER}",
            },
        ],
    )

    # Translation sometimes contains not only the commmand
    shell_command = extract_shell_command_from_text(
        translation.choices[0].message["content"]
    )

    return shell_command
