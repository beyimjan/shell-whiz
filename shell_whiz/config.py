import json
import os
from json import JSONDecodeError

import inquirer
import openai
from inquirer.themes import GreenPassion


def shell_whiz_config_file():
    if "XDG_CONFIG_HOME" in os.environ:
        config_dir = os.environ["XDG_CONFIG_HOME"]
    else:
        config_dir = os.path.join(os.environ["HOME"], ".config")

    sw_config_dir = os.path.join(config_dir, "shell-whiz")
    sw_config_file = os.path.join(sw_config_dir, "config.json")

    return sw_config_dir, sw_config_file


def shell_whiz_config_form():
    questions = [inquirer.Text("openai_api_key", message="OpenAI API Key")]

    answers = inquirer.prompt(questions, theme=GreenPassion())

    return {"openai_api_key": answers["openai_api_key"]}


def shell_whiz_update_config():
    sw_config_dir, sw_config_file = shell_whiz_config_file()

    config = shell_whiz_config_form()

    if not os.path.exists(sw_config_dir):
        os.makedirs(sw_config_dir)

    try:
        with open(sw_config_file, "w") as f:
            f.write(json.dumps(config))
    except IOError:
        return config

    return config


def shell_whiz_read_config():
    _, sw_config_file = shell_whiz_config_file()

    try:
        with open(sw_config_file, "r") as f:
            config = json.load(f)
    except (IOError, JSONDecodeError):
        return {}

    return config


def shell_whiz_config():
    config = shell_whiz_read_config()
    if "openai_api_key" not in config:
        config = shell_whiz_update_config()

    openai.api_key = config["openai_api_key"]
