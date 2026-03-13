import logging
import os

logger = logging.getLogger(__name__)


def is_on_fargate():
    """
    Whether our current environment is Fargate
    """
    return os.environ.get("LAMBDA_ON_FARGATE", False)
