import json
import os
from json import JSONDecodeError

import openai
import questionary
import rich

from shell_whiz.constants import SW_ERROR


def sw_get_config_paths():
    if "XDG_CONFIG_HOME" in os.environ:
        config_dir = os.environ["XDG_CONFIG_HOME"]
    elif "APPDATA" in os.environ:  # for Windows
        config_dir = os.environ["APPDATA"]
    elif "HOME" in os.environ:
        config_dir = os.path.join(os.environ["HOME"], ".config")
    else:
        config_dir = os.getcwd()

    sw_config_dir = os.path.join(config_dir, "shell-whiz")
    sw_config_file = os.path.join(sw_config_dir, "config.json")

    return sw_config_dir, sw_config_file


async def sw_get_user_config():
    rich.print(
        "Visit https://platform.openai.com/account/api-keys to get your API key."
    )
    openai_api_key = await questionary.text(
        "OpenAI API key",
        default=os.environ.get("OPENAI_API_KEY", ""),
    ).unsafe_ask_async()

    return {"openai_api_key": openai_api_key}


async def sw_edit_config():
    sw_config_dir, sw_config_file = sw_get_config_paths()

    sw_config = await sw_get_user_config()

    if not os.path.exists(sw_config_dir):
        os.makedirs(sw_config_dir)

    try:
        with open(sw_config_file, "w") as f:
            f.write(json.dumps(sw_config))
    except IOError:
        rich.print(f"{SW_ERROR}: Couldn't write to file {sw_config_file}")

    return sw_config


def sw_read_config():
    _, sw_config_file = sw_get_config_paths()

    try:
        with open(sw_config_file, "r") as f:
            config = json.load(f)
    except (IOError, JSONDecodeError):
        return {}

    return config


async def sw_config():
    config = sw_read_config()
    if "openai_api_key" not in config:
        config = await sw_edit_config()

    openai.api_key = config["openai_api_key"]
