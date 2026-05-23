# This copyright notice must be included 
# in all distributions of this code
#
# Copyright (c) 2026 John Gentilin
# Author: John Gentilin
# All rights reserved unless otherwise stated.
#
#
from .exporter import probe_endpoint
from .logging import LoggerProvider, NoOpLoggerProvider
from .metric import MeterProvider, NoOpMeterProvider
from .processor import NoOpMetricReader
from .trace import TracerProvider, NoOpTracerProvider

_TRACER_PROVIDER = TracerProvider()
_LOGGER_PROVIDER = LoggerProvider()
_METER_PROVIDER = MeterProvider()
_NOOP_TRACER_PROVIDER = NoOpTracerProvider()
_NOOP_LOGGER_PROVIDER = NoOpLoggerProvider()
_NOOP_METER_PROVIDER = NoOpMeterProvider()
_TELEMETRY_ENABLED = True


def _normalize_otlp_endpoint(endpoint, signal_path):
    endpoint = str(endpoint or '').rstrip('/')
    signal_path = str(signal_path or '')
    if not signal_path.startswith('/'):
        signal_path = '/{}'.format(signal_path)
    if endpoint.endswith(signal_path):
        endpoint = endpoint[:-len(signal_path)]
    return '{}{}'.format(endpoint, signal_path)


def _set_enabled(enabled):
    global _TELEMETRY_ENABLED
    _TELEMETRY_ENABLED = bool(enabled)


def enable_telemetry():
    _set_enabled(True)
    return True


def disable_telemetry(message=None):
    was_enabled = is_telemetry_enabled()
    _set_enabled(False)
    if message and was_enabled:
        print(message)
    return True


def is_telemetry_enabled():
    return bool(_TELEMETRY_ENABLED)


def set_tracer_provider(provider):
    global _TRACER_PROVIDER
    _TRACER_PROVIDER = provider


def get_tracer_provider():
    if not is_telemetry_enabled():
        return _NOOP_TRACER_PROVIDER
    return _TRACER_PROVIDER


def get_tracer(name):
    return get_tracer_provider().get_tracer(name)


def set_logger_provider(provider):
    global _LOGGER_PROVIDER
    _LOGGER_PROVIDER = provider


def get_logger_provider():
    if not is_telemetry_enabled():
        return _NOOP_LOGGER_PROVIDER
    return _LOGGER_PROVIDER


def get_logger(name):
    return get_logger_provider().get_logger(name)


def set_meter_provider(provider):
    global _METER_PROVIDER
    _METER_PROVIDER = provider


def get_meter_provider():
    if not is_telemetry_enabled():
        return _NOOP_METER_PROVIDER
    return _METER_PROVIDER


def get_meter(name):
    return get_meter_provider().get_meter(name)


def setup_otlp(
    endpoint,
    service_name,
    timeout_s=2,
    trace_path='/v1/traces',
    metric_path='/v1/metrics',
    log_path='/v1/logs',
    resource=None,
):
    from .exporter import HTTPLogExporter, HTTPMetricExporter, HTTPSpanExporter
    from .processor import MetricReader, SimpleLogProcessor, SimpleSpanProcessor

    resource_data = {'service.name': str(service_name)}
    for key, value in (resource or {}).items():
        resource_data[str(key)] = value

    base_endpoint = str(endpoint or '').rstrip('/')
    if not probe_endpoint(base_endpoint, timeout_s=timeout_s):
        disable_telemetry('otel endpoint is down')
        return {
            'tracer_provider': get_tracer_provider(),
            'logger_provider': get_logger_provider(),
            'meter_provider': get_meter_provider(),
            'metric_reader': NoOpMetricReader(),
            'resource': resource_data,
            'enabled': False,
        }

    enable_telemetry()

    trace_exporter = HTTPSpanExporter(
        endpoint=_normalize_otlp_endpoint(base_endpoint, trace_path),
        headers={'Content-Type': 'application/json'},
        timeout_s=timeout_s,
    )
    tracer_provider = TracerProvider(resource=resource_data)
    tracer_provider.add_span_processor(SimpleSpanProcessor(trace_exporter))
    set_tracer_provider(tracer_provider)

    log_exporter = HTTPLogExporter(
        endpoint=_normalize_otlp_endpoint(base_endpoint, log_path),
        headers={'Content-Type': 'application/json'},
        timeout_s=timeout_s,
    )
    logger_provider = LoggerProvider(resource=resource_data)
    logger_provider.add_log_processor(SimpleLogProcessor(log_exporter))
    set_logger_provider(logger_provider)

    metric_exporter = HTTPMetricExporter(
        endpoint=_normalize_otlp_endpoint(base_endpoint, metric_path),
        headers={'Content-Type': 'application/json'},
        timeout_s=timeout_s,
    )
    meter_provider = MeterProvider(resource=resource_data)
    metric_reader = MetricReader(metric_exporter)
    meter_provider.add_metric_reader(metric_reader)
    set_meter_provider(meter_provider)
    return {
        'tracer_provider': tracer_provider,
        'logger_provider': logger_provider,
        'meter_provider': meter_provider,
        'metric_reader': metric_reader,
        'resource': resource_data,
        'enabled': True,
    }
