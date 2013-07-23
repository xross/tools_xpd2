import logging
import os

counts = {
    'errors': 0,
    'warnings' : 0
}

def log_error(message, exc_info=False):
    logging.error("ERROR: %s" % message, exc_info=exc_info)
    counts['errors'] += 1

def log_warning(message):
    logging.warning("WARNING: %s" % message)
    counts['warnings'] += 1

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

def print_status_summary():
    if counts['errors'] or counts['warnings']:
        print "%d ERROR%s and %d WARNING%s detected" % (
            counts['errors'], ('s' if counts['errors'] else ''),
            counts['warnings'], ('s' if counts['warnings'] else ''))

