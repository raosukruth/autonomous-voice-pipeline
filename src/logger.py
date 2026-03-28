# Structured logging with call context support.
import logging


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a logger with a structured formatter.

    Format: [TIMESTAMP] [LEVEL] [NAME] message
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        fmt = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
        handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S"))
        logger.addHandler(handler)

    return logger


class CallLogger:
    # Logger with call_id context for per-call log tracking.

    def __init__(self, call_id: str):
        self.call_id = call_id
        self.logger = get_logger(f"call.{call_id}")

    def info(self, msg: str, **kwargs) -> None:
        self.logger.info(f"[{self.call_id}] {msg}", **kwargs)

    def error(self, msg: str, **kwargs) -> None:
        self.logger.error(f"[{self.call_id}] {msg}", **kwargs)

    def warning(self, msg: str, **kwargs) -> None:
        self.logger.warning(f"[{self.call_id}] {msg}", **kwargs)

    def debug(self, msg: str, **kwargs) -> None:
        self.logger.debug(f"[{self.call_id}] {msg}", **kwargs)
