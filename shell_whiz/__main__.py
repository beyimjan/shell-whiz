import json
from json import JSONDecodeError
import sys
import subprocess

import openai

DELIMITER = "####"
SHELL = "bash"

NL_TO_SHELL_COMMAND_PMT = """You are a {SHELL} command translator. Your role is to translate natural language into a {SHELL} command. Think that all necessary programs are installed.

Provide only a ready-to-execute command. Do not write any explanation.

Queries will be separated by {DELIMITER} characters."""


class ShellWhizTranslationError(Exception):
    pass


def extract_shell_command(haystack):
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
        extracted_shell_command = extracted_json.get("shell_command", None)
    except JSONDecodeError:
        raise ShellWhizTranslationError()

    return extracted_shell_command


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
    shell_command = extract_shell_command(
        translation.choices[0].message["content"]
    )

    return shell_command


def main():
    query = sys.argv[1:]
    if not query:
        print("Error: Please provide a query.", file=sys.stderr)
        sys.exit(1)

    try:
        shell_command = translate_natural_language_to_shell_command(
            " ".join(query)
        )

        print(f"Command: {shell_command}")

        yes_no = input("Execute command? [y/N] ")
        if yes_no.lower() == "y":
            subprocess.run(shell_command, shell=True)
    except openai.OpenAIError:
        print("Could not connect to OpenAI API.", file=sys.stderr)
        sys.exit(2)
    except ShellWhizTranslationError:
        print("ShellWhiz doesn't understand your query.", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
