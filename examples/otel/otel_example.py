import os
import sys
import time
import ntptime
import wifi

OTEL_EXPORTER_OTLP_ENDPOINT ="http://192.168.8.192:4318"

from otel import (
    HTTPLogExporter,
    HTTPMetricExporter,
    HTTPSpanExporter,
    LoggerProvider,
    MeterProvider,
    MetricReader,
    SimpleLogProcessor,
    SimpleSpanProcessor,
    TracerProvider,
    get_logger,
    get_meter,
    get_tracer,
    set_logger_provider,
    set_meter_provider,
    set_tracer_provider,
    traced_request,
)


def setup_tracing():
    trace_exporter = HTTPSpanExporter(
        endpoint="{}/v1/traces".format(OTEL_EXPORTER_OTLP_ENDPOINT),
        headers={"Content-Type": "application/json"},
        timeout_s=2,
    )
    provider = TracerProvider(resource={"service.name": "mpy-demo"})
    provider.add_span_processor(SimpleSpanProcessor(trace_exporter))
    set_tracer_provider(provider)

    log_exporter = HTTPLogExporter(
        endpoint="{}/v1/logs".format(OTEL_EXPORTER_OTLP_ENDPOINT),
        headers={"Content-Type": "application/json"},
        timeout_s=2,
    )
    logger_provider = LoggerProvider(resource={"service.name": "mpy-demo"})
    logger_provider.add_log_processor(SimpleLogProcessor(log_exporter))
    set_logger_provider(logger_provider)

    metric_exporter = HTTPMetricExporter(
        endpoint="{}/v1/metrics".format(OTEL_EXPORTER_OTLP_ENDPOINT),
        headers={"Content-Type": "application/json"},
        timeout_s=2,
    )
    meter_provider = MeterProvider(resource={"service.name": "mpy-demo"})
    metric_reader = MetricReader(metric_exporter)
    meter_provider.add_metric_reader(metric_reader)
    set_meter_provider(meter_provider)
    return metric_reader


def main():

    try:
        print("Local time before synchronization：%s" %str(time.localtime()))
        ntptime.settime()
        print("Local time after synchronization：%s" %str(time.localtime()))
    except:
        print("Error setting ntp time")

    metric_reader = setup_tracing()
    tracer = get_tracer("app")
    logger = get_logger("app")
    meter = get_meter("app")
    run_counter = meter.create_counter("app.runs", unit="1")
    duration_ms = meter.create_histogram("app.work.duration", unit="ms")

    with tracer.start_as_current_span("work") as span:
        span.set_attribute("device.id", "esp32-01")
        span.add_event("starting")
        span.set_status("OK")
        logger.info("work started", {"device.id": "esp32-01"})
        run_counter.add(1, {"device.id": "esp32-01"})
        duration_ms.record(3.2, {"device.id": "esp32-01"})

    metric_reader.collect()

    # Optional outgoing HTTP call with span + traceparent injection.
    # response = traced_request(tracer, "GET", "http://httpbin.org/get")
    # response.close()


if __name__ == "__main__":
    main()
