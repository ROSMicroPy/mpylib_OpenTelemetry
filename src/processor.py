
# This copyright notice must be included 
# in all distributions of this code
#
# Copyright (c) 2026 John Gentilin
# Author: John Gentilin
# All rights reserved unless otherwise stated.
#
#
class SimpleSpanProcessor:
    def __init__(self, exporter):
        self._exporter = exporter

    def on_end(self, span, resource=None):
        self._exporter.export([span], resource=resource)

    def shutdown(self):
        if hasattr(self._exporter, "shutdown"):
            self._exporter.shutdown()


class SimpleLogProcessor:
    def __init__(self, exporter):
        self._exporter = exporter

    def emit(self, record, resource=None):
        self._exporter.export([record], resource=resource)

    def shutdown(self):
        if hasattr(self._exporter, "shutdown"):
            self._exporter.shutdown()


class MetricReader:
    def __init__(self, exporter):
        self._exporter = exporter
        self._provider = None

    def _bind(self, provider):
        self._provider = provider

    def collect(self):
        if self._provider is None:
            return None
        metrics = self._provider.collect()
        if not metrics:
            return None
        return self._exporter.export(metrics, resource=self._provider.resource)

    def shutdown(self):
        if hasattr(self._exporter, "shutdown"):
            self._exporter.shutdown()
