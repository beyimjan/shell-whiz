translation_json_schema = {
    "type": "object",
    "properties": {
        "shell_command": {
            "type": "string",
            "description": "Shell command to perform the task, leave blank if it is not possible to perform the task in the command line",
        }
    },
    "required": ["shell_command"],
}

dangerous_command_json_schema = {
    "type": "object",
    "properties": {
        "dangerous_to_run": {"type": "boolean"},
        "dangerous_consequences": {
            "type": "string",
            "description": "Brief explanation of the potential side effects of running the command. No more than 12 words.",
        },
    },
    "required": ["dangerous_to_run"],
}

edited_shell_command_json_schema = {
    "type": "object",
    "properties": {
        "edited_shell_command": {
            "type": "string",
            "description": "Edited shell command, leave blank if you couldn't edit it",
        }
    },
    "required": ["edited_shell_command"],
}
