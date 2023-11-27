import json

import jsonschema

import shell_whiz.openai_client as openai
from shell_whiz.exceptions import (
    EditingError,
    ExplanationError,
    TranslationError,
    WarningError,
)
from shell_whiz.llm_jsonschemas import (
    dangerous_command_jsonschema,
    edited_shell_command_jsonschema,
    translation_jsonschema,
)


async def suggest_shell_command(prompt, preferences, model):
    translation = await openai.suggest_shell_command(
        prompt=prompt, preferences=preferences, model=model
    )

    try:
        translation_json = json.loads(translation)
    except json.JSONDecodeError:
        raise TranslationError("Could not extract JSON.")

    try:
        jsonschema.validate(
            instance=translation_json, schema=translation_jsonschema
        )
    except jsonschema.ValidationError:
        raise TranslationError("Generated JSON is not valid.")

    shell_command = translation_json["shell_command"].strip()

    if shell_command == "":
        raise TranslationError("Extracted shell command is empty.")

    return shell_command


async def recognize_dangerous_command(shell_command, preferences, model):
    dangerous_command = await openai.recognize_dangerous_command(
        shell_command=shell_command, preferences=preferences, model=model
    )

    try:
        dangerous_command_json = json.loads(dangerous_command)
    except json.JSONDecodeError:
        raise WarningError("Could not extract JSON.")

    try:
        jsonschema.validate(
            instance=dangerous_command_json, schema=dangerous_command_jsonschema
        )
    except jsonschema.ValidationError:
        raise WarningError("Generated JSON is not valid.")

    is_dangerous = dangerous_command_json["dangerous_to_run"]
    dangerous_consequences = dangerous_command_json.get(
        "dangerous_consequences", ""
    ).strip()

    if not is_dangerous:
        return False, ""
    elif dangerous_consequences == "":
        raise WarningError("Extracted dangerous consequences are empty.")
    elif "\n" in dangerous_consequences:
        raise WarningError("Extracted dangerous consequences contain newlines.")
    else:
        return True, dangerous_consequences


async def get_explanation_of_shell_command(
    shell_command, preferences, model, stream
):
    return await openai.get_explanation_of_shell_command(
        shell_command=shell_command,
        preferences=preferences,
        model=model,
        stream=stream,
    )


async def get_explanation_of_shell_command_by_chunks(
    shell_command=None, preferences=None, model=None, stream=None
):
    is_first_chunk = True
    skip_initial_spaces = True
    async for chunk in openai.get_explanation_of_shell_command_by_chunks(
        shell_command=shell_command,
        preferences=preferences,
        model=model,
        stream=stream,
    ):
        if chunk is None:
            break

        if skip_initial_spaces:
            chunk = chunk.lstrip()
            if chunk:
                skip_initial_spaces = False
            else:
                continue

        if is_first_chunk:
            if not chunk.startswith("*"):
                raise ExplanationError("Explanation is not valid.")
            is_first_chunk = False

        yield chunk


async def edit_shell_command(shell_command, prompt, model):
    edited_shell_command = await openai.edit_shell_command(
        shell_command=shell_command, prompt=prompt, model=model
    )

    try:
        edited_shell_command_json = json.loads(edited_shell_command)
    except json.JSONDecodeError:
        raise EditingError("Could not extract JSON.")

    try:
        jsonschema.validate(
            instance=edited_shell_command_json,
            schema=edited_shell_command_jsonschema,
        )
    except jsonschema.ValidationError:
        raise EditingError("Generated JSON is not valid.")

    edited_shell_command = edited_shell_command_json[
        "edited_shell_command"
    ].strip()
    if edited_shell_command == "":
        raise EditingError("Edited shell command is empty.")

    return edited_shell_command
