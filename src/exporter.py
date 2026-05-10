
# This copyright notice must be included 
# in all distributions of this code
#
# Copyright (c) 2026 John Gentilin
# Author: John Gentilin
# All rights reserved unless otherwise stated.
#
#
import os

try:
    import ujson as json
except ImportError:
    import json

from .util import now_unix_nanos


_STATUS_CODE_MAP = {"UNSET": 0, "OK": 1, "ERROR": 2}
_SEVERITY_NUMBER_MAP = {
    "TRACE": 1,
    "DEBUG": 5,
    "INFO": 9,
    "WARN": 13,
    "WARNING": 13,
    "ERROR": 17,
    "FATAL": 21,
}


def _debug_export_error(exc):
    debug_value = None
    getenv = getattr(os, "getenv", None)
    if callable(getenv):
        debug_value = getenv("OTEL_EXPORT_DEBUG")
    elif hasattr(os, "environ"):
        try:
            debug_value = os.environ.get("OTEL_EXPORT_DEBUG")
        except Exception:
            debug_value = None
    if debug_value in ("1", "true", "TRUE", "yes", "YES"):
        try:
            import sys

            sys.stderr.write("otel export failed: {}\n".format(exc))
        except Exception:
            pass


def _post_json(endpoint, payload, headers=None, timeout_s=2):
    body = json.dumps(payload)

    # Prefer MicroPython urequests, fallback to urllib for host-side testing.
    try:
        import urequests as requests  # type: ignore

        try:
            response = requests.post(
                endpoint,
                data=body,
                headers=headers or {"Content-Type": "application/json"},
                timeout=timeout_s,
            )
            status = getattr(response, "status_code", 0)
            if hasattr(response, "close"):
                response.close()
            return status
        except Exception as exc:
            _debug_export_error(exc)
            return 0
    except ImportError:
        from urllib import request

        try:
            req = request.Request(
                endpoint,
                data=body.encode("utf-8"),
                headers=headers or {"Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=timeout_s) as response:
                return response.getcode()
        except Exception as exc:
            _debug_export_error(exc)
            return 0


def _as_otel_value(value):
    if value is None:
        return {"stringValue": ""}
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"intValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, dict):
        return {
            "kvlistValue": {
                "values": [_key_value_item(key, item) for key, item in value.items()]
            }
        }
    if isinstance(value, (list, tuple)):
        return {"arrayValue": {"values": [_as_otel_value(item) for item in value]}}
    return {"stringValue": str(value)}


def _key_value_item(key, value):
    return {"key": str(key), "value": _as_otel_value(value)}


def _attributes_kv(attributes):
    return [_key_value_item(key, value) for key, value in (attributes or {}).items()]


def _resource_data(resource):
    return {"attributes": _attributes_kv(resource)}


def _append_scope_item(scope_map, scope_name, payload_key, items):
    scope_entry = scope_map.get(scope_name)
    if scope_entry is None:
        scope_entry = {"scope": {"name": scope_name}, payload_key: []}
        scope_map[scope_name] = scope_entry
    scope_entry[payload_key].extend(items)


def _trace_payload(spans, resource=None):
    scope_spans = {}
    for span in spans:
        otel_span = {
            "traceId": span.trace_id,
            "spanId": span.span_id,
            "name": span.name,
            "kind": 1,
            "startTimeUnixNano": str(span.start_time_unix_nano),
            "endTimeUnixNano": str(span.end_time_unix_nano or now_unix_nanos()),
            "attributes": _attributes_kv(span.attributes),
            "events": [],
            "status": {
                "code": _STATUS_CODE_MAP.get(span.status_code, 0),
                "message": span.status_message,
            },
        }
        if span.parent_span_id:
            otel_span["parentSpanId"] = span.parent_span_id
        for event in span.events:
            otel_span["events"].append(
                {
                    "name": event.get("name", ""),
                    "timeUnixNano": str(event.get("time_unix_nano", now_unix_nanos())),
                    "attributes": _attributes_kv(event.get("attributes", {})),
                }
            )
        scope_name = getattr(getattr(span, "_tracer", None), "name", "mp_opentelemetry")
        _append_scope_item(scope_spans, scope_name, "spans", [otel_span])

    return {
        "resourceSpans": [
            {
                "resource": _resource_data(resource or {}),
                "scopeSpans": list(scope_spans.values()),
            }
        ]
    }


def _log_payload(records, resource=None):
    scope_logs = {}
    for record in records:
        otel_record = {
            "timeUnixNano": str(record.timestamp_unix_nano),
            "observedTimeUnixNano": str(record.timestamp_unix_nano),
            "severityNumber": _SEVERITY_NUMBER_MAP.get(record.severity_text.upper(), 0),
            "severityText": record.severity_text,
            "body": _as_otel_value(record.body),
            "attributes": _attributes_kv(record.attributes),
        }
        if record.trace_id:
            otel_record["traceId"] = record.trace_id
        if record.span_id:
            otel_record["spanId"] = record.span_id
        _append_scope_item(scope_logs, record.logger_name, "logRecords", [otel_record])

    return {
        "resourceLogs": [
            {
                "resource": _resource_data(resource or {}),
                "scopeLogs": list(scope_logs.values()),
            }
        ]
    }


def _number_data_point(point, current_time_unix_nano):
    data_point = {
        "attributes": _attributes_kv(point.get("attributes", {})),
        "timeUnixNano": str(current_time_unix_nano),
    }
    start_time_unix_nano = point.get("start_time_unix_nano")
    if start_time_unix_nano is not None:
        data_point["startTimeUnixNano"] = str(start_time_unix_nano)

    value = point.get("value", 0)
    if isinstance(value, int) and not isinstance(value, bool):
        data_point["asInt"] = str(value)
    else:
        data_point["asDouble"] = float(value)
    return data_point


def _metric_payload(metrics, resource=None):
    current_time_unix_nano = now_unix_nanos()
    scope_metrics = {}
    for metric in metrics:
        entry = {
            "name": metric.get("name", ""),
            "description": metric.get("description", ""),
            "unit": metric.get("unit", ""),
        }
        kind = metric.get("kind")
        points = metric.get("points", [])
        if kind == "counter":
            entry["sum"] = {
                "aggregationTemporality": 2,
                "isMonotonic": True,
                "dataPoints": [
                    _number_data_point(point, current_time_unix_nano) for point in points
                ],
            }
        elif kind == "up_down_counter":
            entry["sum"] = {
                "aggregationTemporality": 2,
                "isMonotonic": False,
                "dataPoints": [
                    _number_data_point(point, current_time_unix_nano) for point in points
                ],
            }
        elif kind == "gauge":
            entry["gauge"] = {
                "dataPoints": [
                    _number_data_point(point, current_time_unix_nano) for point in points
                ]
            }
        elif kind == "histogram":
            entry["histogram"] = {
                "aggregationTemporality": 2,
                "dataPoints": [
                    {
                        "attributes": _attributes_kv(point.get("attributes", {})),
                        "startTimeUnixNano": str(
                            point.get("start_time_unix_nano", current_time_unix_nano)
                        ),
                        "timeUnixNano": str(current_time_unix_nano),
                        "count": str(point.get("count", 0)),
                        "sum": float(point.get("sum", 0)),
                        "bucketCounts": [str(point.get("count", 0))],
                        "explicitBounds": [],
                        "min": float(point.get("min", 0) or 0),
                        "max": float(point.get("max", 0) or 0),
                    }
                    for point in points
                ]
            }
        else:
            continue
        _append_scope_item(
            scope_metrics,
            metric.get("meter_name", "mp_opentelemetry"),
            "metrics",
            [entry],
        )

    return {
        "resourceMetrics": [
            {
                "resource": _resource_data(resource or {}),
                "scopeMetrics": list(scope_metrics.values()),
            }
        ]
    }


class _BaseHTTPExporter:
    def __init__(self, endpoint, headers=None, timeout_s=2):
        self.endpoint = endpoint
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout_s = timeout_s

    def shutdown(self):
        return


class HTTPSpanExporter(_BaseHTTPExporter):
    def export(self, spans, resource=None):
        payload = _trace_payload(spans, resource=resource)
        return _post_json(self.endpoint, payload, self.headers, self.timeout_s)


class HTTPLogExporter(_BaseHTTPExporter):
    def export(self, records, resource=None):
        payload = _log_payload(records, resource=resource)
        return _post_json(self.endpoint, payload, self.headers, self.timeout_s)


class HTTPMetricExporter(_BaseHTTPExporter):
    def export(self, metrics, resource=None):
        payload = _metric_payload(metrics, resource=resource)
        return _post_json(self.endpoint, payload, self.headers, self.timeout_s)
