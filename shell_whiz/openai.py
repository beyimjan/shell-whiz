import json
from json import JSONDecodeError

import jsonschema
import openai
from colorama import Fore, Style
from jsonschema import validate
from yaspin import yaspin

from shell_whiz.constants import SHELL_WHIZ_WAIT_MESSAGE
from shell_whiz.exceptions import (
    ShellWhizExplanationError,
    ShellWhizTranslationError,
)

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
                "content": 'Extract JSON from user messages with keys "shell_command" (required), "dangerous_to_run" (required, boolean), and "dangerous_consequences" (required if "dangerous_to_run" is true; explain in simple words, maximum 12 words).\n\nOnly generate JSON to make your output machine readable.',
            },
            {
                "role": "user",
                "content": f"{DELIMITER}\n{haystack}\n{DELIMITER}\n\nMost commands are safe to execute.",
            },
        ],
    )

    json_schema = {
        "type": "object",
        "properties": {
            "shell_command": {"type": "string"},
            "dangerous_to_run": {"type": "boolean"},
            "dangerous_consequences": {"type": "string"},
        },
        "required": ["shell_command", "dangerous_to_run"],
    }

    try:
        extracted_json = json.loads(
            extracted_json.choices[0].message["content"]
        )
    except JSONDecodeError:
        raise ShellWhizTranslationError("Could not extract JSON.")

    try:
        validate(instance=extracted_json, schema=json_schema)
    except jsonschema.ValidationError:
        raise ShellWhizTranslationError("Generated JSON is not valid.")

    shell_command = extracted_json.get("shell_command", "").strip()
    is_dangerous = extracted_json.get("dangerous_to_run", False)
    dangerous_consequences = extracted_json.get(
        "dangerous_consequences", ""
    ).strip()

    if shell_command == "":
        raise ShellWhizTranslationError("Extracted shell command is empty.")

    if is_dangerous and dangerous_consequences == "":
        raise ShellWhizTranslationError(
            "Extracted dangerous consequences are empty."
        )

    return (
        shell_command,
        is_dangerous,
        dangerous_consequences,
    )


@yaspin(text=SHELL_WHIZ_WAIT_MESSAGE, color="green")
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
    return extract_shell_command_from_text(
        translation.choices[0].message["content"]
    )


def format_explanatory_message(explanation):
    json_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "ch": {"type": "string"},
                "ex": {"type": "string"},
                "children": {"type": "array"},
            },
            "required": ["ch", "ex"],
        },
    }

    def traverse_explanation(explanation, level=0):
        explanation_str = ""

        if explanation is None:
            return ""

        try:
            validate(instance=explanation, schema=json_schema)
        except jsonschema.ValidationError:
            raise ShellWhizExplanationError("Generated JSON is not valid.")

        if len(explanation) == 0:
            return ""

        for chunk in explanation:
            command = chunk.get("ch", "").strip()
            explanation = chunk.get("ex", "").strip()

            if command == "" or explanation == "":
                raise ShellWhizExplanationError(
                    "Extracted command or explanation is empty."
                )

            command_lines = command.splitlines()

            explanation_str += (
                " "
                + "  " * level
                + f"* {Fore.GREEN + command_lines[0] + Style.RESET_ALL}"
            )
            for line in command_lines[1:]:
                explanation_str += (
                    "\n"
                    + "  " * level
                    + f"   {Fore.GREEN + line + Style.RESET_ALL}"
                )

            explanation_str += f" {explanation}\n"

            if "children" in chunk:
                explanation_str += traverse_explanation(
                    chunk.get("children", None), level + 1
                )

        return explanation_str

    return traverse_explanation(explanation)


@yaspin(text=SHELL_WHIZ_WAIT_MESSAGE, color="green")
def get_explanation_of_shell_command(command):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": 'Your role is to generate a Python list containing dictionaries with the following structure:\n[\n\t{\n\t\t"ch": "command or part of the beginning of command", "ex": "clear but short explanations of what this chunk does or what it is used for",\n\t\t"children": [\n\t\t\t{"ch": "arguments associated with the command", "ex": "","children": [...]},\n\t\t\t...\n\t\t]\n\t}\n]',
            },
            {
                "role": "user",
                "content": f"{DELIMITER}\nw | tail -n +3 | cut -d ' ' -f 1 | grep -v ^avst$ | sort -u | wc -l\n{DELIMITER}",
            },
            {
                "role": "assistant",
                "content": '[\n\t{"ch": "w", "ex": "displays information about currently logged-in users."},\n\t{\n\t\t"ch": "tail", "ex": "outputs the last part of files.",\n\t\t"children": [{"ch": "-n +3", "ex": "displays lines starting from the third line."}]\n\t},\n\t{\n\t\t"ch": "| cut", "ex": "extracts usernames from the previous command output.",\n\t\t"children": [\n\t\t\t{"ch": "-d \' \'", "ex": "specifies the delimiter as a space."},\n\t\t\t{"ch": "-f 1", "ex": "indicates that we want to select the first field."}\n\t\t]\n\t},\n\t{\n\t\t"ch": "| grep -v ^avst$", "ex": "excludes username \'avst\'.",\n\t\t"children": [\n\t\t\t{"ch": "-v", "ex": "inverts the match."},\n\t\t\t{"ch": "^avst$", "ex": "is a regex that exactly matches \'avst\'."}\n\t\t]\n\t},\n\t{\n\t\t"ch": "| sort", "ex": "sorts output in lexicographical order.",\n\t\t"children": [{"ch": "-u", "ex": "outputs only the unique lines."}]\n\t},\n\t{"ch": "| wc -l", "ex": "counts the number of lines."}\n]',
            },
            {
                "role": "user",
                "content": f"{DELIMITER}\ndocker stop $(docker ps -a -q)\n{DELIMITER}",
            },
            {
                "role": "assistant",
                "content": '[{"ch": "docker stop", "ex": "stops a running container.",\n\t"children": [{\n\t\t"ch": "$( ... )", "ex": "replaces itself with the command output inside.",\n\t\t"children": [{\n\t\t\t"ch": "docker ps", "ex": "lists all running containers.",\n\t\t\t"children": [\n\t\t\t\t{"ch": "-a", "ex": "shows all containers (including stopped ones)."},\n\t\t\t\t{"ch": "-q", "ex": "only displays container IDs."}\n\t\t\t]\n\t\t}]\n\t}]\n}]',
            },
            {
                "role": "user",
                "content": f"{DELIMITER}\n{command}\n{DELIMITER}",
            },
        ],
        max_tokens=1024,
    )

    try:
        explanation = json.loads(response.choices[0].message["content"])
    except JSONDecodeError:
        raise ShellWhizExplanationError("Could not extract JSON.")

    return format_explanatory_message(explanation)
