import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):

    def format(self, record):

        data = {
            "timestamp": datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        fields = (
            "request_id",
            "method",
            "route",
            "status_code",
            "duration_ms",
        )

        for field in fields:
            if hasattr(record, field):
                data[field] = getattr(record, field)

        if record.exc_info:
            data["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(data)


def configure_logging(app):

    logger = app.logger

    logger.setLevel(logging.INFO)

    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())

    formatter = JsonFormatter()

    for handler in logger.handlers:
        handler.setFormatter(formatter)

    logger.propagate = False