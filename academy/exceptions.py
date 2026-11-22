class AcademyError(Exception):
    """Recoverable input or processing error."""


class DecodeError(AcademyError):
    pass


class ParseError(AcademyError):
    pass


class SnapshotError(AcademyError):
    pass
