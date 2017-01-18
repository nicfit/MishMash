from sys import stdout, stderr


def _print(string, file, log_func=None):
    print(string, file=file)
    if log_func:
        log_func(string)


def pout(string, log=None):
    _print(string, stdout, log_func=log.info if log else None)


def perr(string, log=None):
    _print(string, stderr, log_func=log.error if log else None)
