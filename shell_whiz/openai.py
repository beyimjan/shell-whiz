import json
from json import JSONDecodeError

import openai
from colorama import Fore, Style
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
    shell_command = extract_shell_command_from_text(
        translation.choices[0].message["content"]
    )

    return shell_command


def format_explanatory_message(explanation):
    def traverse_explanation(explanation, level=0):
        explanation_str = ""

        if explanation is None:
            return ""

        if not isinstance(explanation, list):
            raise ShellWhizExplanationError(
                "Explanation is not a list of dictionaries."
            )

        if len(explanation) == 0:
            return ""

        for chunk in explanation:
            if not isinstance(chunk, dict):
                raise ShellWhizExplanationError("Chunk is not a dictionary.")

            command = chunk.get("ch", None)
            explanation = chunk.get("ex", None)
            children = chunk.get("children", None)

            if (
                command is None
                or explanation is None
                or not isinstance(command, str)
                or not isinstance(explanation, str)
            ):
                raise ShellWhizExplanationError(
                    "Chunk or explanation is not a str."
                )

            explanation_str += (
                " "
                + "  " * level
                + f"* {Fore.GREEN + command + Style.RESET_ALL} {explanation}\n"
            )
            if "children" in chunk:
                explanation_str += traverse_explanation(children, level + 1)

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
