import json

import jsonschema
import openai
import yaspin
from jsonschema import validate

from shell_whiz.constants import DELIMITER, SHELL, SHELL_WHIZ_WAIT_MESSAGE
from shell_whiz.exceptions import (
    ShellWhizTranslationError,
    ShellWhizWarningError,
)


def translate_natural_language_to_shell_command_openai(prompt):
    return (
        openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=0.25,
            max_tokens=256,
            messages=[
                {
                    "role": "system",
                    "content": f'You are a {SHELL} command translator. Your role is to translate natural language into a {SHELL} command. Think that all necessary programs are installed.\n\nProvide only a ready-to-execute command. Do not write any explanation.\n\nCreate a JSON with the "shell_command" key, if query cannot be translated into a shell command, output an empty JSON object.\n\nOnly generate JSON to make your output machine readable.\n\nQueries will be separated by {DELIMITER} characters.',
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


@yaspin.yaspin(text=SHELL_WHIZ_WAIT_MESSAGE, color="green")
def translate_natural_language_to_shell_command(prompt):
    translation_json_schema = {
        "type": "object",
        "properties": {"shell_command": {"type": "string"}},
        "required": ["shell_command"],
    }

    translation = translate_natural_language_to_shell_command_openai(prompt)

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
    return (
        openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=0.25,
            max_tokens=96,
            messages=[
                {
                    "role": "user",
                    "content": f'Bash command to execute: ####\n{shell_command}\n####\n\nIs this Bash command dangerous to execute?\n\nGenerate a JSON with the required key "dangerous_to_run" (boolean) and the optional key "dangerous_consequences" (explain in simple words, maximum 12 words) if the command is dangerous to execute.\n\nOnly generate JSON to make your output machine readable.',
                }
            ],
        )
        .choices[0]
        .message["content"]
    )


@yaspin.yaspin(text=SHELL_WHIZ_WAIT_MESSAGE, color="green")
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


def get_explanation_of_shell_command_openai(shell_command):
    return (
        openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=0.1,
            max_tokens=256,
            messages=[
                {
                    "role": "system",
                    "content": 'Create a bulleted list that explains, piece by piece, what the command does for advanced users of command line.\n\n* Do not explain basic command line concepts such as pipes, command substitution, variables, etc.\n* When you begin explaining arguments, increase the level of nesting. You can include as many levels as needed for an easy-to-read explanation.\n* Use backticks to indicate code.\n\n* All items in the list must follow the format of "piece" followed by a verb (such as "`^avst$` is a regex that exactly matches \'avst\'" or "`-n +3` displays lines starting from the third line").\n* To make it easier to read and understand, you must limit each line to 45 characters.\n* Use two spaces as indents when specifying different nesting levels in your bulleted list.\n* Only create a bulleted list and use 2 spaces for nesting to make your output easy to read.\n\nStart from the most general description of the overall command and continue by adding more details explaining each argument.',
                },
                {
                    "role": "user",
                    "content": f"{DELIMITER}\nw | tail -n +3 | cut -d ' ' -f 1 | grep -v ^avst$ | sort -u | wc -l\n{DELIMITER}",
                },
                {
                    "role": "assistant",
                    "content": "* `w` displays information about currently logged-in users.\n* `| tail -n +3` displays lines starting from the third line.\n* `| cut extracts usernames from the previous command output.\n  * `-d ' '` specifies the delimiter as a space.\n  * `-f 1` selects the first field.\n* `| grep -v ^avst$` excludes username 'avst'.\n    * `-v` inverts the match, so it selects lines that do not match the pattern.\n    * `^avst$` is a regex that exactly matches 'avst'.\n  * `sort -u` sorts the lines in alphabetical order and removes duplicates.\n  * `wc -l` counts the number of lines in the output.",
                },
                {
                    "role": "user",
                    "content": f"{DELIMITER}\ngit log --name-only --pretty=format: | sort | uniq -c | sort -nr | head\n{DELIMITER}",
                },
                {
                    "role": "assistant",
                    "content": "* `git log` displays the commit history of a Git repository.\n  * `--name-only` shows only the names of the files that were changed in each commit.\n  * `--pretty=format:` specifies the format of the log output as empty.\n* `| sort` sorts the file names in alphabetical order.\n* `| uniq -c` counts the number of occurrences of each file name.\n* `| sort -nr` sorts the file names in descending order based on the count.\n* `| head` displays the first few lines of the output, which are the files with the highest count.",
                },
                {
                    "role": "user",
                    "content": f"{DELIMITER}\ndocker stop $(docker ps -a -q)\n{DELIMITER}",
                },
                {
                    "role": "assistant",
                    "content": "* `docker stop` stops a running container.\n  * `$( ... )` replaces itself with the command output inside.\n    * `docker ps` lists all running containers.\n      * `-a` shows all containers (including stopped ones).\n      * `-q` only displays container IDs.",
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


async def get_explanation_of_shell_command(shell_command):
    return get_explanation_of_shell_command_openai(shell_command)
