from datetime import datetime


def utcnow():
    """
    Get current UTC datetime.

    Returns:
        datetime object representing current UTC time
    """
    return datetime.utcnow()


def timestamp():
    """
    Get current UTC timestamp.

    Returns:
        float representing seconds since Unix epoch
    """
    return utcnow().timestamp()

