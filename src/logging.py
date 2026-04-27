
# This copyright notice must be included 
# in all distributions of this code
#
# Copyright (c) 2026 John Gentilin
# Author: John Gentilin
# All rights reserved unless otherwise stated.
#
#
from .context import get_current_span
from .util import now_unix_nanos


class LogRecord:
    def __init__(
        self,
        logger,
        severity_text,
        body,
        attributes=None,
        timestamp_unix_nano=None,
        span=None,
    ):
        self.logger_name = logger.name
        self.severity_text = str(severity_text)
        self.body = body
        self.attributes = attributes or {}
        self.timestamp_unix_nano = timestamp_unix_nano or now_unix_nanos()
        current_span = span or get_current_span()
        self.trace_id = None
        self.span_id = None
        if current_span is not None:
            self.trace_id = current_span.trace_id
            self.span_id = current_span.span_id

    def to_dict(self):
        return {
            "logger_name": self.logger_name,
            "severity_text": self.severity_text,
            "body": self.body,
            "attributes": self.attributes,
            "timestamp_unix_nano": self.timestamp_unix_nano,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
        }


class Logger:
    def __init__(self, provider, name):
        self._provider = provider
        self.name = name

    def emit(self, severity_text, body, attributes=None, span=None):
        record = LogRecord(self, severity_text, body, attributes=attributes, span=span)
        self._provider._emit(record)
        return record

    def debug(self, body, attributes=None):
        return self.emit("DEBUG", body, attributes=attributes)

    def info(self, body, attributes=None):
        return self.emit("INFO", body, attributes=attributes)

    def warn(self, body, attributes=None):
        return self.emit("WARN", body, attributes=attributes)

    def warning(self, body, attributes=None):
        return self.warn(body, attributes=attributes)

    def error(self, body, attributes=None):
        return self.emit("ERROR", body, attributes=attributes)


class LoggerProvider:
    def __init__(self, resource=None):
        self.resource = resource or {}
        self._processors = []

    def get_logger(self, name):
        return Logger(self, name)

    def add_log_processor(self, processor):
        self._processors.append(processor)

    def _emit(self, record):
        for processor in self._processors:
            processor.emit(record, resource=self.resource)

    def shutdown(self):
        for processor in self._processors:
            if hasattr(processor, "shutdown"):
                processor.shutdown()
