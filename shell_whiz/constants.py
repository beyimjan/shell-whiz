from colorama import Fore, Style

SHELL_WHIZ_DESCRIPTION = "Shell Whiz: AI assistant right in your terminal"

SHELL_WHIZ_WAIT_MESSAGE = "Wait, Shell Whiz is thinking"

OPENAI_CONNECTION_ERROR = f"{Fore.YELLOW}Error{Style.RESET_ALL}: Failed to connect to OpenAI API.\nCheck your internet connection and API key. Run {Fore.GREEN}sw config{Style.RESET_ALL} to set up the API key."
