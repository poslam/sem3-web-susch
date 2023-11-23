from datetime import datetime, timedelta


def time():
    return datetime.utcnow()+timedelta(hours=10)
