import sys
import logging

# Fallback logger using standard logging instead of loguru
logger = logging.getLogger("mothercare")

# Configure logging format
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

