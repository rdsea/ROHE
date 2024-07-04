import logging
import sys
import traceback

_level_to_enum = {
    0: logging.NOTSET,
    1: logging.DEBUG,
    2: logging.INFO,
    3: logging.WARNING,
    4: logging.ERROR,
    5: logging.CRITICAL,
}


class RoheObject:
    def __init__(self, logging_level=2):
        # logging.basicConfig(
        #     format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.NOTSET
        # )
        #
        logging.basicConfig(
            format="%(asctime)s : %(levelname)s - %(message)s",
            datefmt="%d-%b-%y %H:%M:%S",
        )
        self.logger = logging.getLogger()
        self.set_logger_level(logging_level)

    def set_logger_level(self, logging_level: int):
        """
        logging_level:
            0: NOTSET
            1: DEBUG
            2: INFO
            3: WARNING
            4: ERROR
            5: CRITICAL
        """
        self.logger.setLevel(_level_to_enum[logging_level])

    def log(self, message, level=2):
        to_enum = _level_to_enum[level]
        try:
            message = str(message)
            if to_enum == logging.NOTSET:
                pass
            elif to_enum == logging.DEBUG:
                self.logger.debug(message)
            elif to_enum == logging.INFO:
                self.logger.info(message)
            elif to_enum == logging.WARNING:
                self.logger.warning(message)
            elif to_enum == logging.ERROR:
                self.logger.error(message)
            elif to_enum == logging.CRITICAL:
                self.logger.critical(message)
        except Exception as e:
            self.log(f"Error {type(e)} while logging: {e.__traceback__}", 4)
            traceback.print_exception(*sys.exc_info())
