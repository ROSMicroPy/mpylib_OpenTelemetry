
# This copyright notice must be included 
# in all distributions of this code
#
# Copyright (c) 2026 John Gentilin
# Author: John Gentilin
# All rights reserved unless otherwise stated.
#
#
from .context import get_current_span


def inject_traceparent(headers, span=None):
    target = headers if headers is not None else {}
    current = span or get_current_span()
    if current is None:
        return target
    target["traceparent"] = "00-{}-{}-01".format(current.trace_id, current.span_id)
    return target


def extract_traceparent(headers):
    if not headers:
        return None
    value = headers.get("traceparent")
    if not value:
        return None
    parts = value.split("-")
    if len(parts) != 4:
        return None
    return {
        "version": parts[0],
        "trace_id": parts[1],
        "span_id": parts[2],
        "trace_flags": parts[3],
    }
