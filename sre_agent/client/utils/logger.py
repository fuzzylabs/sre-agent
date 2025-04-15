"""Logger for the SRE agent client."""

import logging
import os
from logging.handlers import RotatingFileHandler

# Create a logger
logger = logging.getLogger("sre-agent-client")
logger.setLevel(logging.DEBUG)

# Create console handler with a higher log level
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create file handler which logs even debug messages
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
file_handler = RotatingFileHandler(
    os.path.join(log_dir, "client.log"),
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
)
file_handler.setLevel(logging.DEBUG)

# Create formatters and add it to the handlers
console_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
file_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

console_handler.setFormatter(console_formatter)
file_handler.setFormatter(file_formatter)

# Add the handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Prevent propagation to the root logger
logger.propagate = False


# Add color to console output
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""

    COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[91m\033[1m",  # Bold Red
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        # Add color to the levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"  # noqa: E501
        return super().format(record)


# Replace the console formatter with the colored one
console_handler.setFormatter(
    ColoredFormatter(
        "%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
)

# Export the logger
__all__ = ["logger"]
