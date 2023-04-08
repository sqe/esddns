from configparser import ConfigParser
import logging
import sys

def logger():
    """A Wrapper for logging to write both console and a log file 

    Defaults
    --------
    config.read('dns.ini') : file
        configuration file
    log_file : str
        filename for logs in configuration file
    console_output : boolean
        Boolean value to write to both console and file or only file

    Returns
    -------
    Instance : Logger Class instance 
        If config["log"]["log_to_console"] is True
            Logging enabled for both file and console
        If config["log"]["log_to_console"] is False
            Logging to file enabled, console logs are disabled
        If config["log"]["log_to_console"] not in ("True" or "False")
            exits with message to set True or False in configuration
    Log format : %(asctime)s %(levelname)s %(message)s
    Log encoding : utf-8
    Log level : DEBUG
    """
    config = ConfigParser()
    config.read('dns.ini') 
    console_output = config["log"]["log_to_console"]
    log_file = config["log"]["log_file"]
    log_format = '%(asctime)s %(levelname)s %(message)s'
    logger = logging

    if console_output not in ("False", "True"):
        return sys.exit("Incorrect value for log_to_console toggle, set False or True")
    if logger.getLogger().handlers:
        logger.getLogger().handlers = []
    logger.getLogger(__name__)
    logger.basicConfig(filename=log_file,
        encoding='utf-8',
        level=logging.DEBUG,
        format=log_format)
    
    console_handler = logging.StreamHandler()
    logger_formatter = logger.Formatter(log_format)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logger_formatter)
    if console_output == "False":
        logger.getLogger("").removeHandler(console_handler)
        return logger
    elif console_output == "True":
        logger.getLogger("").addHandler(console_handler)
        return logger