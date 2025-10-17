"""
    This file is used to set up the logging configuration for the project.
    It defines the logger setup, including the log level and format.
"""

import logging

def setup_logger(logger_name: str = None, prefix: str = "") -> logging.Logger:
    """Set up a logger with the specified name.
    Both handler and formatter are configured here.

    Parameters
    -----------
    logger_name : str
        Name of the logger (normally python __name__ is used).

    Returns
    --------
    logger : logging.Logger
        Logger object, set up as defined in this configuration.
    """
    logger = logging.getLogger(logger_name)

    logger.setLevel("INFO")

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        prefix + "%(levelname)s %(asctime)s %(filename)s %(funcName)s:%(lineno)s| %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger

