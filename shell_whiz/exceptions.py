class ShellWhizError(Exception):
    pass


class TranslationError(ShellWhizError):
    pass


class WarningError(ShellWhizError):
    pass


class ExplanationError(ShellWhizError):
    pass


class EditingError(ShellWhizError):
    pass
