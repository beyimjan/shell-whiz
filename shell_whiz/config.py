import json
import os
from typing import Any, Optional

from pydantic import BaseModel, ValidationError


class ConfigError(Exception):
    pass


class _ConfigModelNotStrict(BaseModel):
    openai_api_key: Optional[str] = None
    openai_org_id: Optional[str] = None


class ConfigModel(BaseModel):
    openai_api_key: str
    openai_org_id: Optional[str] = None


class Config:
    __instance = None
    __config = None

    def __new__(cls) -> "Config":
        if cls.__instance:
            return cls.__instance

        cls.__instance = super().__new__(cls)

        try:
            config_from_env = Config.__get_config_from_env()
        except ConfigError:
            config_from_env = None

        try:
            _, config_file = Config.__get_config_path()
            config_from_file = Config.__get_config_from_file(config_file)
        except ConfigError:
            config_from_file = None

        try:
            if config_from_env and config_from_file:
                Config.__config = ConfigModel(
                    **config_from_file.model_dump(exclude_none=True)
                    | config_from_env.model_dump(exclude_none=True)
                )
            elif config_from_env:
                Config.__config = ConfigModel(**config_from_env.model_dump())
            elif config_from_file:
                Config.__config = ConfigModel(**config_from_file.model_dump())
            else:
                raise ConfigError("Configuration data is missing.")
        except ValidationError:
            raise ConfigError("Failed to validate configuration data.")

        return cls.__instance

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__config, name)

    @staticmethod
    def write(config: ConfigModel) -> None:
        directory, config_file = Config.__get_config_path()

        try:
            os.makedirs(directory, exist_ok=True)
        except os.error:
            raise ConfigError(f"Failed to create directory {directory}.")

        try:
            with open(config_file, mode="w") as f:
                f.write(config.model_dump_json(exclude_none=True))
        except os.error:
            raise ConfigError(f"Failed to create file {config_file}.")

        try:
            os.chmod(config_file, 0o600)
        except os.error:
            raise ConfigError(
                f"Failed to change permissions for {config_file} to read and write for the current user only."
            )

    @staticmethod
    def __get_config_path() -> tuple[str, str]:
        directory = None
        config_file = None

        error_message = ""

        os_name = os.name
        if os_name == "posix":
            xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
            home = os.environ.get("HOME")

            if xdg_config_home:
                directory = xdg_config_home
            elif home:
                directory = os.path.join(home, ".config")
            else:
                error_message = "Set either $XDG_CONFIG_HOME or $HOME."
        elif os_name == "nt":
            appdata = os.environ.get("APPDATA")
            if appdata:
                directory = appdata
            else:
                error_message = "Set $APPDATA."

        if not directory:
            raise ConfigError(
                "Unable to find the configuration directory. " + error_message
                or "Something went wrong."
            )

        directory = os.path.join(directory, "shell-whiz")
        config_file = os.path.join(directory, "config.json")

        return directory, config_file

    @staticmethod
    def __get_config_from_env() -> _ConfigModelNotStrict:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        openai_org_id = os.environ.get("OPENAI_ORG_ID")

        try:
            return _ConfigModelNotStrict(
                openai_api_key=openai_api_key, openai_org_id=openai_org_id
            )
        except ValidationError:
            raise ConfigError(
                "Validation failed for either $OPENAI_API_KEY or $OPENAI_ORG_ID."
            )

    @staticmethod
    def __get_config_from_file(config_file: str) -> _ConfigModelNotStrict:
        try:
            with open(config_file) as f:
                config = json.load(f)
        except (os.error, json.JSONDecodeError):
            raise ConfigError("Unable to read the configuration file.")

        if not isinstance(config, dict):
            raise ConfigError(
                "Configuration file doesn't match the expected JSON schema."
            )

        try:
            return _ConfigModelNotStrict(**config)
        except ValidationError:
            raise ConfigError(
                "Configuration file doesn't match the expected JSON schema."
            )
