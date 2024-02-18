import os

from beartype import beartype
from omegaconf import OmegaConf


@beartype
def get_env_variable(name: str) -> str | None:
    """Get environment variable.

    Args:
        name (str): Name of environment variable.

    Returns:
        str | None: Environment variable value.
    """

    return os.environ.get(name)


OmegaConf.register_new_resolver("env", get_env_variable)
