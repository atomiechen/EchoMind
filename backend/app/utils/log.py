import logging
import sys
from typing import Optional


def init_logging():
    from uvicorn.config import LOGGING_CONFIG

    # LOG FORMAT CONFIGURATION
    # exactly how uvicorn's log format looks like:
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = (
        "%(asctime)s [%(name)s] %(levelprefix)s %(message)s"
    )
    LOGGING_CONFIG["formatters"]["access"]["fmt"] = (
        '%(asctime)s [%(name)s] %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'
    )
    # setup log format for the application code
    logging.basicConfig(
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        level=logging.INFO,
    )


def get_frame_fallback(n):
    """
    Adopted from [loguru source](https://github.com/Delgan/loguru/blob/master/loguru/__init__.py).
    """
    try:
        raise Exception
    except Exception:
        frame = sys.exc_info()[2].tb_frame.f_back  # type: ignore
        for _ in range(n):
            frame = frame.f_back  # type: ignore
        return frame


def load_get_frame_function():
    """
    Adopted from [loguru source](https://github.com/Delgan/loguru/blob/master/loguru/__init__.py).
    """
    if hasattr(sys, "_getframe"):
        get_frame = sys._getframe
    else:
        get_frame = get_frame_fallback
    return get_frame


get_frame = load_get_frame_function()


def get_logger(name: Optional[str] = None):
    """
    Retrieve the module logger without needing to pass the module name.
    """
    if name is not None:
        return logging.getLogger(name)

    try:
        frame = get_frame(1)
    except ValueError:
        f_globals = {}
    else:
        f_globals = frame.f_globals  # type: ignore

    module_name = f_globals.get("__name__", None)
    return logging.getLogger(module_name)
