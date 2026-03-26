# MicroPython OTel Lite

`mpy_otel_lite` is a very small OpenTelemetry-inspired telemetry library for MicroPython.

It supports:
- basic tracing (`TracerProvider`, `Tracer`, `Span`)
- basic logging (`LoggerProvider`, `Logger`, `LogRecord`)
- basic metrics (`MeterProvider`, `Meter`, `Counter`, `Gauge`, `Histogram`)
- simple attributes/events/status
- HTTP export of completed spans, logs, and metric snapshots (JSON payload)
- optional `traceparent` propagation helpers for HTTP requests
- optional traced outgoing HTTP helper (`traced_request`)

It intentionally omits advanced OTel features to stay lightweight.

## Project Layout

- `mpy_otel_lite/` - library package
- `examples/main.py` - quick example

## Example

```python
from mpy_otel_lite import (
    HTTPLogExporter,
    HTTPMetricExporter,
    TracerProvider,
    LoggerProvider,
    MeterProvider,
    SimpleSpanProcessor,
    SimpleLogProcessor,
    MetricReader,
    HTTPSpanExporter,
    get_logger,
    get_meter,
    set_tracer_provider,
    set_logger_provider,
    set_meter_provider,
    get_tracer,
)

trace_exporter = HTTPSpanExporter(
    endpoint="http://collector.local:4318/v1/traces",
    headers={"Content-Type": "application/json"},
    timeout_s=2,
)
log_exporter = HTTPLogExporter(
    endpoint="http://collector.local:4318/v1/logs",
)
metric_exporter = HTTPMetricExporter(
    endpoint="http://collector.local:4318/v1/metrics",
)

provider = TracerProvider(resource={"service.name": "mpy-sensor"})
provider.add_span_processor(SimpleSpanProcessor(trace_exporter))
set_tracer_provider(provider)

logger_provider = LoggerProvider(resource={"service.name": "mpy-sensor"})
logger_provider.add_log_processor(SimpleLogProcessor(log_exporter))
set_logger_provider(logger_provider)

meter_provider = MeterProvider(resource={"service.name": "mpy-sensor"})
metric_reader = MetricReader(metric_exporter)
meter_provider.add_metric_reader(metric_reader)
set_meter_provider(meter_provider)

tracer = get_tracer("sensor-loop")
logger = get_logger("sensor-loop")
meter = get_meter("sensor-loop")
samples = meter.create_counter("sensor.samples", unit="1")
latency = meter.create_histogram("sensor.latency_ms", unit="ms")

with tracer.start_as_current_span("read_sensors") as span:
    span.set_attribute("device.id", "esp32-01")
    span.add_event("sampling_started")
    value = 42
    span.set_attribute("sample.value", value)
    logger.info("sample collected", {"sample.value": value})
    samples.add(1, {"device.id": "esp32-01"})
    latency.record(12.5, {"device.id": "esp32-01"})

metric_reader.collect()
```

## HTTP helper

```python
from mpy_otel_lite import traced_request

response = traced_request(tracer, "GET", "http://httpbin.org/get")
response.close()
```

This creates a client span and injects `traceparent` into request headers.

## Included vs omitted

Included:
- tracing
- logging
- metrics via manual collection
- simple synchronous span processor
- simple synchronous log processor
- simple manual metric reader
- simple HTTP exporters

Omitted (for size/simplicity):
- async batching/retries
- full OTLP protobuf encoding
- full context propagation stack

## Run on device

1. Copy `mpy_otel_lite/` to your board filesystem.
2. Import and configure exporter endpoint.
3. Start creating spans around important operations.

## Notes

- Uses `urequests` when available (MicroPython).
- Falls back to `urllib` when running on CPython for local testing.
- Export payload format is intentionally simple, OTLP-like JSON.
