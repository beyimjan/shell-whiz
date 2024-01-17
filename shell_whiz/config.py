import json
import os
from typing import Any

import jsonschema


class WritingError(Exception):
    pass


ConfigData = dict[str, str]


class Config:
    __jsonschema: dict[str, Any] = {
        "type": "object",
        "properties": {"OPENAI_API_KEY": {"type": "string"}},
        "required": ["OPENAI_API_KEY"],
    }

    def __init__(self) -> None:
        os_name = os.name

        home = os.environ.get("HOME")
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")

        appdata = os.environ.get("APPDATA")

        self.__config_dir = ""
        if os_name == "posix":
            if xdg_config_home:
                self.__config_dir = xdg_config_home
            elif home:
                self.__config_dir = os.path.join(home, ".config")
        elif os_name == "nt" and appdata:
            self.__config_dir = appdata

        if not self.__config_dir:
            self.__config_dir = os.path.join(os.getcwd(), ".config")

        self.__config_dir = os.path.join(self.__config_dir, "shell-whiz")
        self.__config_file = os.path.join(self.__config_dir, "config.json")

        try:
            with open(self.__config_file) as f:
                self.__data = json.load(f)
            jsonschema.validate(self.data, self.__jsonschema)
        except (os.error, json.JSONDecodeError, jsonschema.ValidationError):
            self.__data = {}

    @property
    def data(self) -> ConfigData:
        return self.__data

    def write(self, data: ConfigData) -> None:
        try:
            jsonschema.validate(data, self.__jsonschema)
        except jsonschema.ValidationError:
            raise WritingError("Invalid configuration.")
        else:
            self.__data = data

        try:
            os.makedirs(self.__config_dir, exist_ok=True)
        except os.error:
            raise WritingError(
                f"Couldn't create directory {self.__config_dir}."
            )

        try:
            with open(self.__config_file, "w") as f:
                json.dump(self.__data, f)
        except os.error:
            raise WritingError(f"Couldn't write to file {self.__config_file}.")

        try:
            os.chmod(self.__config_file, 0o600)
        except os.error:
            raise WritingError(
                f"Failed to change permissions for {self.__config_file}."
            )
