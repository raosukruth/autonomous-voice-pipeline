# Tests for Logger module (Step 1.3a).
import logging
import pytest
from src.logger import get_logger, CallLogger


def test_get_logger_returns_logger():
    # Assert return type is logging.Logger.
    logger = get_logger("test.module")
    assert isinstance(logger, logging.Logger)


def test_get_logger_has_handler():
    # Assert logger has at least one handler.
    logger = get_logger("test.has_handler")
    assert len(logger.handlers) >= 1


def test_call_logger_includes_call_id(caplog):
    # Capture log output, assert call_id appears.
    call_id = "test-call-123"
    call_logger = CallLogger(call_id)
    with caplog.at_level(logging.INFO, logger=f"call.{call_id}"):
        call_logger.info("Test message")
    assert call_id in caplog.text


def test_call_logger_levels():
    # Call info/error/warning/debug, assert no exceptions raised.
    call_logger = CallLogger("level-test-456")
    call_logger.info("info message")
    call_logger.error("error message")
    call_logger.warning("warning message")
    call_logger.debug("debug message")
    # If we get here, no exceptions were raised
    assert True
