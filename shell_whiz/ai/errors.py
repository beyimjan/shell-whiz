class ErrorAI(Exception):
    pass


class SuggestionError(ErrorAI):
    pass


class WarningError(ErrorAI):
    pass


class ExplanationError(ErrorAI):
    pass


class EditingError(ErrorAI):
    pass
