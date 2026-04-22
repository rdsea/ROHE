import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

c_handler = logging.StreamHandler()
c_handler.setLevel(logging.INFO)
c_format = logging.Formatter(
    "%(module)s : %(asctime)s : %(levelname)s  - %(message)s",
)
c_handler.setFormatter(c_format)
logger.addHandler(c_handler)
