import logging
import random
import string
import boto3


logger = logging.getLogger(__name__)
ALPHA_NUM = string.ascii_letters + string.digits


def generate_random_alphanum(length: int = 20) -> str:
    return "".join(random.choices(ALPHA_NUM, k=length))


def get_param_store_secret(parameter_name):
    ssm_client = boto3.client("ssm", region_name="eu-central-1")
    try:
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
        secret_value = response["Parameter"]["Value"]
        return secret_value
    except ssm_client.exceptions.ParameterNotFound:
        logger.error(f"Parameter '{parameter_name}' not found in Parameter Store.")
        raise
    except Exception as e:
        logger.error(f"An error occurred while retrieving the secret: {e}")
        raise
