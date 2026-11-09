"""Exception hierarchy. The core normalizes every failure into one of these."""

from __future__ import annotations


class Km200Error(Exception):
    """Base class of all integration errors."""


class TransportError(Km200Error):
    """The gateway could not be reached, timed out or answered with an HTTP error."""


class PointUnavailableError(Km200Error):
    """The gateway answered 404 or a non-value resource: the point does not exist here."""


class InvalidKeyError(Km200Error):
    """The reply did not decrypt to JSON: the gateway or private password is wrong."""


class MalformedResponseError(Km200Error):
    """The reply decrypted but does not have the expected shape."""


class RejectReason:
    """Why a command was refused before any request was made."""

    WRITE_DISABLED = "write_disabled"
    GROUP_NOT_ALLOWED = "group_not_allowed"
    NOT_WRITEABLE = "not_writeable"
    UNKNOWN_POINT = "unknown_point"
    INVALID_VALUE = "invalid_value"
    OUT_OF_RANGE = "out_of_range"


class CommandRejectedError(Km200Error):
    """A command failed validation. Nothing was sent."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
