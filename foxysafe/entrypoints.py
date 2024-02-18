import os
import sys
from pathlib import Path

import hydra
from beartype import beartype
from hydra.core.hydra_config import HydraConfig
from loguru import logger as log
from omegaconf import DictConfig
from rich.pretty import pretty_repr

from foxysafe import CONFIG_DIR, CONFIG_NAME
from foxysafe.gitlab.backups import gitlab_backup_routine
from foxysafe.utils.custom_logging import disable_logging_groups, setup_custom_hydra_logging


@hydra.main(CONFIG_DIR.as_posix(), CONFIG_NAME, version_base="1.3")
@beartype
def backup_routine_entrypoint(config: DictConfig):
    """Entrypoint for foxysafe backup routing configured by hydra YAML config file.

    Args:
        config (DictConfig): Hydra config object.
    """

    setup_custom_hydra_logging(config)

    log.info(f"Found {CONFIG_NAME} configuration file in {CONFIG_DIR}")
    log.debug(f"Configuration:\n{pretty_repr(config)}")

    hydra_internal_config = HydraConfig.get()

    backup_dir = (Path(hydra_internal_config.runtime.output_dir) / "foxysafe.backup/").resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(backup_dir)

    gitlab_backup_routine(config, backup_dir)


def main():
    """Entrypoint for foxysafe configured by hydra YAML config file."""

    disable_logging_groups("urllib3")

    try:
        hydra_working_dir = "./foxysafe_out/${now:%Y-%m-%d}/${now:%H-%M-%S}/"
        sys.argv += [f"hydra.run.dir={hydra_working_dir}"]

        backup_routine_entrypoint()
    except KeyboardInterrupt:
        log.info("Exiting...")
        exit(0)
    except Exception:
        log.exception("An unhandled runtime exception occurred.")
        exit(1)


if __name__ == "__main__":
    main()
