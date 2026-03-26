from .context import get_current_span, set_current_span
from .util import now_unix_nanos, random_span_id, random_trace_id


class Span:
    def __init__(self, tracer, name, trace_id, span_id, parent_span_id=None):
        self._tracer = tracer
        self.name = name
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.start_time_unix_nano = now_unix_nanos()
        self.end_time_unix_nano = None
        self.attributes = {}
        self.events = []
        self.status_code = "UNSET"
        self.status_message = ""
        self._ended = False

    def set_attribute(self, key, value):
        self.attributes[str(key)] = value

    def add_event(self, name, attributes=None):
        self.events.append(
            {
                "name": str(name),
                "time_unix_nano": now_unix_nanos(),
                "attributes": attributes or {},
            }
        )

    def set_status(self, code, message=""):
        self.status_code = str(code)
        self.status_message = str(message)

    def record_exception(self, exc):
        self.add_event(
            "exception",
            {
                "exception.type": exc.__class__.__name__,
                "exception.message": str(exc),
            },
        )
        self.set_status("ERROR", str(exc))

    def end(self):
        if self._ended:
            return
        self.end_time_unix_nano = now_unix_nanos()
        self._ended = True
        self._tracer._on_end(self)

    def to_dict(self):
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time_unix_nano": self.start_time_unix_nano,
            "end_time_unix_nano": self.end_time_unix_nano,
            "attributes": self.attributes,
            "events": self.events,
            "status": {
                "code": self.status_code,
                "message": self.status_message,
            },
        }


class _SpanScope:
    def __init__(self, span):
        self._span = span
        self._previous = None

    def __enter__(self):
        self._previous = set_current_span(self._span)
        return self._span

    def __exit__(self, exc_type, exc, tb):
        if exc is not None:
            self._span.record_exception(exc)
        self._span.end()
        set_current_span(self._previous)
        return False


class Tracer:
    def __init__(self, provider, name):
        self._provider = provider
        self.name = name

    def start_span(self, name):
        parent = get_current_span()
        if parent is None:
            trace_id = random_trace_id()
            parent_span_id = None
        else:
            trace_id = parent.trace_id
            parent_span_id = parent.span_id
        return Span(
            tracer=self,
            name=name,
            trace_id=trace_id,
            span_id=random_span_id(),
            parent_span_id=parent_span_id,
        )

    def start_as_current_span(self, name):
        return _SpanScope(self.start_span(name))

    def _on_end(self, span):
        self._provider._on_span_end(span)


class TracerProvider:
    def __init__(self, resource=None):
        self.resource = resource or {}
        self._processors = []

    def get_tracer(self, name):
        return Tracer(self, name)

    def add_span_processor(self, processor):
        self._processors.append(processor)

    def _on_span_end(self, span):
        for processor in self._processors:
            processor.on_end(span, resource=self.resource)

    def shutdown(self):
        for processor in self._processors:
            if hasattr(processor, "shutdown"):
                processor.shutdown()
