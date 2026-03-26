_CURRENT_SPAN = None


def get_current_span():
    return _CURRENT_SPAN


def set_current_span(span):
    global _CURRENT_SPAN
    previous = _CURRENT_SPAN
    _CURRENT_SPAN = span
    return previous
