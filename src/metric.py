
# This copyright notice must be included 
# in all distributions of this code
#
# Copyright (c) 2026 John Gentilin
# Author: John Gentilin
# All rights reserved unless otherwise stated.
#
#
from .util import now_unix_nanos


class _MetricPointSet:
    def __init__(self):
        self._points = {}
        self.start_time_unix_nano = now_unix_nanos()

    def _normalize_attributes(self, attributes):
        normalized = {}
        for key, value in (attributes or {}).items():
            normalized[str(key)] = value
        return normalized

    def _point_key(self, attributes):
        normalized = self._normalize_attributes(attributes)
        items = list(normalized.items())
        items.sort()
        return tuple(items), normalized

    def snapshot(self):
        points = []
        for key in self._points:
            point = self._points[key]
            points.append(point.copy())
        return points


class Counter(_MetricPointSet):
    kind = "counter"

    def __init__(self, meter_name, name, unit="", description=""):
        super().__init__()
        self.meter_name = meter_name
        self.name = name
        self.unit = unit
        self.description = description

    def add(self, amount, attributes=None):
        point_key, normalized = self._point_key(attributes)
        point = self._points.get(point_key)
        if point is None:
            point = {
                "attributes": normalized,
                "value": 0,
                "start_time_unix_nano": now_unix_nanos(),
            }
            self._points[point_key] = point
        point["value"] += amount

    def collect(self):
        return {
            "meter_name": self.meter_name,
            "name": self.name,
            "description": self.description,
            "unit": self.unit,
            "kind": self.kind,
            "points": self.snapshot(),
        }


class UpDownCounter(Counter):
    kind = "up_down_counter"


class Gauge(_MetricPointSet):
    kind = "gauge"

    def __init__(self, meter_name, name, unit="", description=""):
        super().__init__()
        self.meter_name = meter_name
        self.name = name
        self.unit = unit
        self.description = description

    def set(self, value, attributes=None):
        point_key, normalized = self._point_key(attributes)
        existing = self._points.get(point_key)
        start_time_unix_nano = now_unix_nanos()
        if existing is not None:
            start_time_unix_nano = existing.get("start_time_unix_nano", start_time_unix_nano)
        self._points[point_key] = {
            "attributes": normalized,
            "value": value,
            "start_time_unix_nano": start_time_unix_nano,
        }

    def collect(self):
        return {
            "meter_name": self.meter_name,
            "name": self.name,
            "description": self.description,
            "unit": self.unit,
            "kind": self.kind,
            "points": self.snapshot(),
        }


class Histogram(_MetricPointSet):
    kind = "histogram"

    def __init__(self, meter_name, name, unit="", description=""):
        super().__init__()
        self.meter_name = meter_name
        self.name = name
        self.unit = unit
        self.description = description

    def record(self, value, attributes=None):
        point_key, normalized = self._point_key(attributes)
        point = self._points.get(point_key)
        if point is None:
            point = {
                "attributes": normalized,
                "count": 0,
                "sum": 0,
                "min": None,
                "max": None,
                "start_time_unix_nano": now_unix_nanos(),
            }
            self._points[point_key] = point
        point["count"] += 1
        point["sum"] += value
        point["min"] = value if point["min"] is None else min(point["min"], value)
        point["max"] = value if point["max"] is None else max(point["max"], value)

    def collect(self):
        return {
            "meter_name": self.meter_name,
            "name": self.name,
            "description": self.description,
            "unit": self.unit,
            "kind": self.kind,
            "points": self.snapshot(),
        }


class Meter:
    def __init__(self, provider, name):
        self._provider = provider
        self.name = name

    def create_counter(self, name, unit="", description=""):
        return self._provider._register(
            Counter(self.name, name, unit=unit, description=description)
        )

    def create_up_down_counter(self, name, unit="", description=""):
        return self._provider._register(
            UpDownCounter(self.name, name, unit=unit, description=description)
        )

    def create_gauge(self, name, unit="", description=""):
        return self._provider._register(
            Gauge(self.name, name, unit=unit, description=description)
        )

    def create_histogram(self, name, unit="", description=""):
        return self._provider._register(
            Histogram(self.name, name, unit=unit, description=description)
        )


class MeterProvider:
    def __init__(self, resource=None):
        self.resource = resource or {}
        self._instruments = []
        self._readers = []

    def get_meter(self, name):
        return Meter(self, name)

    def add_metric_reader(self, reader):
        reader._bind(self)
        self._readers.append(reader)

    def _register(self, instrument):
        self._instruments.append(instrument)
        return instrument

    def collect(self):
        metrics = []
        for instrument in self._instruments:
            metrics.append(instrument.collect())
        return metrics

    def shutdown(self):
        for reader in self._readers:
            reader.shutdown()
