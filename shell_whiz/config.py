import json
import os
from typing import Any

import jsonschema


class WritingError(Exception):
    pass


class ReadingError(Exception):
    pass


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

    async def write(self, config: dict[str, Any]) -> None:
        try:
            os.makedirs(self.__config_dir, exist_ok=True)
        except os.error:
            raise WritingError(
                "Couldn't create directory {self.__config_dir}."
            )

        try:
            with open(self.__config_file, "w") as f:
                json.dump(config, f)
        except os.error:
            raise WritingError("Couldn't write to file {self.__config_file}.")

        try:
            os.chmod(self.__config_file, 0o600)
        except os.error:
            raise WritingError(
                "Failed to change permissions for {self.__config_file}."
            )

    async def read(self) -> dict[str, Any]:
        config_json = self.__read_json()
        config = self.__validate_json(config_json)
        return config

    def __read_json(self) -> Any:
        try:
            with open(self.__config_file) as f:
                config = json.load(f)
        except os.error:
            raise ReadingError("Couldn't read file {self.__config_file}.")
        except json.JSONDecodeError:
            raise ReadingError(
                "Couldn't parse JSON from {self.__config_file}."
            )
        else:
            return config

    def __validate_json(self, config: Any) -> dict[str, Any]:
        try:
            jsonschema.validate(config, self.__jsonschema)
        except jsonschema.ValidationError:
            raise ReadingError(
                "JSON schema validation failed for {self.__config_file}."
            )
        else:
            return config
