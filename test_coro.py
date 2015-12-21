import sys

def func(*args):
    try:
        yield args
    except Exception as e:
        print id(e), e
        raise


a = func('a')
next(a)
b = func('b')
next(b)

try:
    raise ValueError('hello')
except ValueError as e:

    try:
        a.throw(*sys.exc_info())
    except Exception as e2:
        print e is e2

    try:
        b.throw(*sys.exc_info())
    except Exception as e2:
        print e is e2

    raise
