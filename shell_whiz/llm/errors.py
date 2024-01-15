class ErrorLLM(Exception):
    pass


class TranslationError(ErrorLLM):
    pass


class WarningError(ErrorLLM):
    pass


class ExplanationError(ErrorLLM):
    pass


class EditingError(ErrorLLM):
    pass
