class UnknownBackend(BaseException):
    """the python configure is unknown"""


class ExtraMetadataRequired(BaseException):
    """the python configure is unknown"""


class NotImplementedYetError(BaseException):
    """a feature we want, but don't have."""


class UntitledException(BaseException):
    """cannot infer a name for an untitled project."""
