import logging
import os

def log_error(message, exc_info=False):
    logging.error("ERROR: %s" % message, exc_info=exc_info)

def log_warning(message):
    logging.warning("WARNING: %s" % message)

def log_info(message):
    logging.info("%s" % message)

def log_debug(message):
    logging.debug("%s" % message)

def configure_logging(console_level="INFO", file_level="DEBUG"):
    """ Set up logging so only desired level and above go to the console but DEBUG and above go to
        a log file
    """
    cwd = os.getcwd()
    logging.basicConfig(level=eval("logging.%s" % file_level), format='%(message)s',
            filename=os.path.join(cwd, 'xpd.log'), filemode='w')
    console = logging.StreamHandler()
    console.setLevel(eval("logging.%s" % console_level))
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

