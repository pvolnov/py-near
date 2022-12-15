from datetime import datetime


def utcnow():
    return datetime.utcnow()


def timestamp():
    return utcnow().timestamp()