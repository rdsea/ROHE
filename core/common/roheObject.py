import logging
import sys
import traceback


class RoheObject(object):
    def __init__(self, logging_level=2):
        logging.basicConfig(
            format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.NOTSET
        )
        self.logger = logging.getLogger()
        self.set_logger_level(logging_level)

    def set_logger_level(self, logging_level):
        if logging_level == 0:
            log_level = logging.NOTSET
        elif logging_level == 1:
            log_level = logging.DEBUG
        elif logging_level == 2:
            log_level = logging.INFO
        elif logging_level == 3:
            log_level = logging.WARNING
        elif logging_level == 4:
            log_level = logging.ERROR
        elif logging_level == 5:
            log_level = logging.CRITICAL
        self.logger.setLevel(log_level)

    def log(self, message, level=2):
        try:
            message = str(message)
            if level == 0:
                pass
            elif level == 1:
                self.logger.debug(message)
            elif level == 2:
                self.logger.info(message)
            elif level == 3:
                self.logger.error(message)
            elif level == 4:
                self.logger.warning(message)
            elif level == 5:
                self.logger.critical(message)
        except Exception as e:
            self.log("Error {} while logging: {}".format(type(e), e.__traceback__), 4)
            traceback.print_exception(*sys.exc_info())
