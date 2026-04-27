
# This copyright notice must be included 
# in all distributions of this code
#
# Copyright (c) 2026 John Gentilin
# Author: John Gentilin
# All rights reserved unless otherwise stated.
#
#
from .logging import LoggerProvider
from .metric import MeterProvider
from .trace import TracerProvider

_TRACER_PROVIDER = TracerProvider()
_LOGGER_PROVIDER = LoggerProvider()
_METER_PROVIDER = MeterProvider()


def set_tracer_provider(provider):
    global _TRACER_PROVIDER
    _TRACER_PROVIDER = provider


def get_tracer_provider():
    return _TRACER_PROVIDER


def get_tracer(name):
    return _TRACER_PROVIDER.get_tracer(name)


def set_logger_provider(provider):
    global _LOGGER_PROVIDER
    _LOGGER_PROVIDER = provider


def get_logger_provider():
    return _LOGGER_PROVIDER


def get_logger(name):
    return _LOGGER_PROVIDER.get_logger(name)


def set_meter_provider(provider):
    global _METER_PROVIDER
    _METER_PROVIDER = provider


def get_meter_provider():
    return _METER_PROVIDER


def get_meter(name):
    return _METER_PROVIDER.get_meter(name)
