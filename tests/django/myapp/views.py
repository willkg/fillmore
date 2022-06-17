class IntentionalException(Exception):
    pass


def broken_view(req):
    raise IntentionalException("broken view")
