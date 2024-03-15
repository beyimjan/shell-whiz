class ErrorLLM(Exception):
    pass


class SuggestionError(ErrorLLM):
    pass


class WarningError(ErrorLLM):
    pass
