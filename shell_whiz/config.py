import json
import os
from typing import Any, Dict

import jsonschema


class WritingError(Exception):
    pass


class ReadingError(Exception):
    pass


class Config:
    __jsonschema: Dict[str, Any] = {
        "type": "object",
        "properties": {"OPENAI_API_KEY": {"type": "string"}},
        "required": ["OPENAI_API_KEY"],
    }

    def __init__(self) -> None:
        self.__config_dir = os.path.join(
            (
                os.environ.get("XDG_CONFIG_HOME")
                or os.environ.get("APPDATA")
                or os.path.join(os.environ.get("HOME", os.getcwd()), ".config")
            ),
            "shell-whiz",
        )
        self.__config_file = os.path.join(self.__config_dir, "config.json")

    async def write(self, config: Dict[str, Any]) -> None:
        try:
            os.makedirs(self.__config_dir, exist_ok=True)
        except OSError:
            raise WritingError(
                "Couldn't create directory {self.__config_dir}."
            )

        try:
            with open(self.__config_file, "w") as f:
                json.dump(config, f)
        except OSError:
            raise WritingError("Couldn't write to file {self.__config_file}.")

        try:
            os.chmod(self.__config_file, 0o600)
        except OSError:
            raise WritingError(
                "Failed to change permissions for {self.__config_file}."
            )

    async def read(self) -> Dict[str, Any]:
        config_json = self.__read_json()
        config = self.__validate_json(config_json)
        return config

    def __read_json(self) -> Any:
        try:
            with open(self.__config_file) as f:
                config = json.load(f)
        except OSError:
            raise ReadingError("Couldn't read file {self.__config_file}.")
        except json.JSONDecodeError:
            raise ReadingError(
                "Couldn't parse JSON from {self.__config_file}."
            )
        else:
            return config

    def __validate_json(self, config: Any) -> Dict[str, Any]:
        try:
            jsonschema.validate(config, self.__jsonschema)
        except jsonschema.ValidationError:
            raise ReadingError(
                "JSON schema validation failed for {self.__config_file}."
            )
        else:
            return config
