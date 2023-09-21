translation_json_schema = {
    "type": "object",
    "properties": {
        "shell_command": {
            "type": "string",
            "description": "Shell command to perform the task",
        },
        "invalid_request": {
            "type": "boolean",
            "description": "Set to true if it is not possible to perform the task in the command line",
        },
    },
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
