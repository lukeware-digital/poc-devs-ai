import logging
import logging.handlers
from pathlib import Path

LOG_FILE = Path("devs_ai.log")
MAX_BYTES = 10 * 1024 * 1024
BACKUP_COUNT = 5


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("DEVs_AI")
    logger.setLevel(level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(agent_id)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - [%(agent_id)s] - %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


class AgentAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        agent_id = self.extra.get("agent_id", "system")
        kwargs["extra"] = {"agent_id": agent_id}
        return msg, kwargs
