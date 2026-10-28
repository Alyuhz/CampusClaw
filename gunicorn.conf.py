import os
import sys

from dotenv import load_dotenv

load_dotenv()

web_port = os.environ.get("WEB_PORT", "").strip()
if not web_port:
    raise RuntimeError("missing required environment variable: WEB_PORT")

bind = f"127.0.0.1:{web_port}"
workers = 1
errorlog = "-"
accesslog = None
capture_output = True
graceful_timeout = 30
timeout = 30

logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "campusclaw.http.JsonFormatter",
        }
    },
    "handlers": {
        "json_stdout": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": sys.stdout,
        }
    },
    "loggers": {
        "gunicorn.error": {
            "handlers": ["json_stdout"],
            "level": "INFO",
            "propagate": False,
        },
        "gunicorn.access": {
            "handlers": [],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["json_stdout"],
        "level": "INFO",
    },
}
