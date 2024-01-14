import os

import questionary
import rich

from .cli_tools import pretty_log_error
from .config import Config, ReadingError, WritingError


class ConfigCLI:
    def __init__(self):
        self.__model = Config()

    async def edit(self):
        config = await self.__edit_cli()

        try:
            await self.__model.write(config)
        except WritingError as e:
            pretty_log_error(e)
            return config

        return config

    async def __edit_cli(self):
        rich.print(
            "Visit https://platform.openai.com/account/api-keys to get your API key."
        )
        openai_api_key = await questionary.text(
            "OpenAI API key",
            default=os.environ.get("OPENAI_API_KEY", ""),
            validate=lambda text: len(text) > 0,
        ).unsafe_ask_async()

        return {"OPENAI_API_KEY": openai_api_key}

    async def get(self):
        try:
            return await self.__model.read()
        except ReadingError as e:
            pretty_log_error(e)
            return await self.edit()
