"""Custom uvicorn logging configuration for the v1.3 Artist Console.

Routes every uvicorn logger to `ext://sys.stderr` so the MCP stdio wire
on stdout stays byte-clean. Stdout corruption in stdio mode (P-01) has
no graceful failure mode — the MCP client silently disconnects with a
framing error. This dict is belt-and-suspenders per D-19..D-22.
"""

STDERR_ONLY_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(name)s %(message)s",
            "use_colors": False,
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "uvicorn":        {"handlers": ["default"], "level": "WARNING", "propagate": False},
        "uvicorn.error":  {"handlers": ["default"], "level": "WARNING", "propagate": False},
        "uvicorn.access": {"handlers": ["default"], "level": "WARNING", "propagate": False},
        # uvicorn.access also disabled via access_log=False on uvicorn.Config (D-21).
    },
}
