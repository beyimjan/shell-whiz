import json
from json import JSONDecodeError
import sys
import subprocess

import openai

DELIMITER = "####"

NL_TO_BASH_SYSTEM_MESSAGE = f"""You are a Bash command translator. Your role is to translate natural language into a Bash command. Think that all necessary programs are installed.

Provide only a ready-to-execute command. Do not write explanations.

Queries will be separated by {DELIMITER} characters."""


def translate_natural_language_to_bash(query):
    chain_of_thoughts = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=0.35,
        messages=[
            {"role": "system", "content": NL_TO_BASH_SYSTEM_MESSAGE},
            {
                "role": "user",
                "content": f"{DELIMITER}{query}{DELIMITER}",
            },
        ],
    )

    result_in_json = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": 'Extract JSON from user messages with a single key "bash_command".\n\nOnly generate JSON to make your output machine readable.',
            },
            {
                "role": "user",
                "content": chain_of_thoughts.choices[0].message["content"],
            },
        ],
    )
    try:
        result_in_json = json.loads(
            result_in_json.choices[0].message["content"]
        )
    except JSONDecodeError:
        raise Exception("Could not decode JSON.")

    return result_in_json.get("bash_command", None)


def main():
    query = sys.argv[1:]
    if not query:
        print("Please provide a query.")
        sys.exit(1)

    try:
        command = translate_natural_language_to_bash(" ".join(query))

        print(f"Command: {command}")

        yes_no = input("Execute command? [y/N] ")
        if yes_no.lower() == "y":
            subprocess.run(command, shell=True)
    except openai.OpenAIError:
        print("Could not connect to OpenAI API.")
    except Exception:
        print("Something went wrong.")


if __name__ == "__main__":
    main()
