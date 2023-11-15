import json
import os

import questionary
import rich

from shell_whiz.constants import ERROR_PREFIX_RICH


def get_config_paths():
    config_dir = os.path.join(
        (
            os.environ.get("XDG_CONFIG_HOME")
            or os.environ.get("APPDATA")
            or os.path.join(os.environ.get("HOME", os.getcwd()), ".config")
        ),
        "shell-whiz",
    )
    config_file = os.path.join(config_dir, "config.json")

    return config_dir, config_file


async def edit_config_cli():
    rich.print(
        "Visit https://platform.openai.com/account/api-keys to get your API key."
    )
    openai_api_key = await questionary.text(
        "OpenAI API key",
        default=os.environ.get("OPENAI_API_KEY", ""),
        validate=lambda text: len(text) > 0,
    ).unsafe_ask_async()

    return {"OPENAI_API_KEY": openai_api_key}


async def edit_config():
    config = await edit_config_cli()

    config_dir, config_file = get_config_paths()

    try:
        os.makedirs(config_dir, exist_ok=True)
    except OSError:
        rich.print(
            f"{ERROR_PREFIX_RICH}: Couldn't create directory {config_dir}"
        )
        return config

    try:
        with open(config_file, "w") as f:
            json.dump(config, f)
    except OSError:
        rich.print(f"{ERROR_PREFIX_RICH}: Couldn't write to file {config_file}")
        return config

    try:
        os.chmod(config_file, 0o600)
    except OSError:
        rich.print(
            f"{ERROR_PREFIX_RICH}: Failed to change permissions for {config_file}"
        )

    return config


def read_config():
    _, config_file = get_config_paths()

    try:
        with open(config_file) as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    else:
        return config


async def configure():
    config = read_config()
    if "OPENAI_API_KEY" not in config:
        config = await edit_config()

    os.environ["OPENAI_API_KEY"] = config["OPENAI_API_KEY"]
