class NotFoundError(Exception):
    """Requested entity does not exist."""


class ConflictError(Exception):
    """Entity clashes with an existing one (e.g. duplicate email)."""
