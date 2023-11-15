from openai import AsyncOpenAI

from shell_whiz.llm_jsonschemas import (
    dangerous_command_jsonschema,
    edited_shell_command_jsonschema,
    translation_jsonschema,
)


def get_formatted_preferences(preferences):
    return f"These are my preferences: ####\n{preferences}\n####"


async def suggest_shell_command(prompt, preferences, model):
    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model=model,
        temperature=0.25,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": f"{get_formatted_preferences(preferences)}\n\n{prompt}",
            }
        ],
        functions=[
            {
                "name": "perform_task_in_command_line",
                "description": "Perform a task in the command line",
                "parameters": translation_jsonschema,
            }
        ],
        function_call={"name": "perform_task_in_command_line"},
    )
    return response.choices[0].message.function_call.arguments


async def recognize_dangerous_command(shell_command, preferences, model):
    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model=model,
        temperature=0,
        max_tokens=96,
        messages=[
            {
                "role": "user",
                "content": f"{get_formatted_preferences(preferences)}\n\nI want to run this command: ####\n{shell_command}\n####",
            },
        ],
        functions=[
            {
                "name": "recognize_dangerous_command",
                "description": "Recognize a dangerous shell command. This function should be very low sensitive, only mark a command dangerous when it has very serious consequences.",
                "parameters": dangerous_command_jsonschema,
            }
        ],
        function_call={"name": "recognize_dangerous_command"},
    )
    return response.choices[0].message.function_call.arguments


async def get_explanation_of_shell_command(
    shell_command, preferences, model, stream
):
    prompt = f'Break down the command into parts and explain it in a **list** format. Each line should follow the format "part of the command", with an explanation afterward. ALWAYS start your answer with an asterisk when you start explaining a shell command. ONLY AND ONLY IF you are unable to explain the command or if it is not a shell command, reply with an empty JSON.\n\nFor example, if the command is `ls -l`, you would explain it as:\n* `ls` lists directory contents.\n  * `-l` displays in long format.\n\nFor `cat file | grep "foo"`, the explanation would be:\n* `cat file` reads the content of `file`.\n* `| grep "foo"` filters lines containing "foo".\n\n* Never explain basic command line concepts like pipes, variables, etc.\n* Keep explanations clear, simple, concise and elegant (under 7 words per line).\n* Use two spaces to indent for each nesting level in your list.\n\n{get_formatted_preferences(preferences)}\n\nShell command: ####\n{shell_command}\n####'

    temperature = 0.1
    max_tokens = 512

    client = AsyncOpenAI()
    return await client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
        messages=[{"role": "user", "content": prompt}],
    )


async def get_explanation_of_shell_command_by_chunks(
    shell_command=None, preferences=None, model=None, stream=None
):
    if stream is None:
        stream = await get_explanation_of_shell_command(
            shell_command=shell_command,
            preferences=preferences,
            model=model,
            stream=True,
        )

    async for chunk in stream:
        yield chunk.choices[0].delta.content


async def edit_shell_command(shell_command, prompt, model):
    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model=model,
        temperature=0.2,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": f"{shell_command}\n\nPrompt: ####\n{prompt}\n####",
            },
        ],
        functions=[
            {
                "name": "edit_shell_command",
                "description": "Edit a shell command, according to the prompt",
                "parameters": edited_shell_command_jsonschema,
            }
        ],
        function_call={"name": "edit_shell_command"},
    )
    return response.choices[0].message.function_call.arguments
