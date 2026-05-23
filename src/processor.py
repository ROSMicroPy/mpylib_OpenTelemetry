# This copyright notice must be included 
# in all distributions of this code
#
# Copyright (c) 2026 John Gentilin
# Author: John Gentilin
# All rights reserved unless otherwise stated.
#
#

def _telemetry_enabled():
    try:
        from .api import is_telemetry_enabled

        return is_telemetry_enabled()
    except Exception:
        return True


class SimpleSpanProcessor:
    def __init__(self, exporter, batch_size=16):
        self._exporter = exporter
        self._batch_size = max(1, int(batch_size or 1))
        self._pending_spans = []

    def on_end(self, span, resource=None):
        if not _telemetry_enabled():
            self._pending_spans = []
            return 0
        self._pending_spans.append(span)
        should_flush = len(self._pending_spans) >= self._batch_size
        if getattr(span, 'parent_span_id', None) is None:
            should_flush = True
        if not should_flush:
            return 0
        pending = self._pending_spans
        self._pending_spans = []
        status = self._exporter.export(pending, resource=resource)
        if not _telemetry_enabled():
            self._pending_spans = []
        elif not status:
            self._pending_spans = pending + self._pending_spans
        return status

    def shutdown(self):
        if _telemetry_enabled() and self._pending_spans:
            pending = self._pending_spans
            self._pending_spans = []
            self._exporter.export(pending)
        if hasattr(self._exporter, 'shutdown'):
            self._exporter.shutdown()


class SimpleLogProcessor:
    def __init__(self, exporter):
        self._exporter = exporter

    def emit(self, record, resource=None):
        if not _telemetry_enabled():
            return 0
        return self._exporter.export([record], resource=resource)

    def shutdown(self):
        if hasattr(self._exporter, 'shutdown'):
            self._exporter.shutdown()


class MetricReader:
    def __init__(self, exporter):
        self._exporter = exporter
        self._provider = None

    def _bind(self, provider):
        self._provider = provider

    def collect(self):
        if not _telemetry_enabled() or self._provider is None:
            return None
        metrics = self._provider.collect()
        if not metrics:
            return None
        return self._exporter.export(metrics, resource=self._provider.resource)

    def shutdown(self):
        if hasattr(self._exporter, 'shutdown'):
            self._exporter.shutdown()


class NoOpMetricReader:
    def __init__(self):
        self._provider = None

    def _bind(self, provider):
        self._provider = provider

    def collect(self):
        return None

    def shutdown(self):
        return True
