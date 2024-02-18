from pathlib import Path
from warnings import filterwarnings

from beartype.roar import BeartypeDecorHintPep585DeprecationWarning
from dotenv import load_dotenv
from rich.traceback import install as rich_traceback_install

from foxysafe import custom_hydra_plugins

CONFIG_DIR = (Path(__file__).parent.parent).resolve()
CONFIG_NAME = "default_config"

__all__ = ["custom_hydra_plugins", "CONFIG_DIR", "CONFIG_NAME"]

load_dotenv((CONFIG_DIR / ".env").as_posix())

filterwarnings("ignore", category=BeartypeDecorHintPep585DeprecationWarning)

rich_traceback_install()
