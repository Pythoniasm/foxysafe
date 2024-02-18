import logging

from beartype import beartype
from hydra.core.hydra_config import HydraConfig
from loguru import logger as log
from omegaconf import DictConfig
from rich.logging import RichHandler


@beartype
class InterceptHandler(logging.Handler):
    """Intercept standard logging and redirect to loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to streams.

        Args:
            record (logging.LogRecord): Basic log record.
        """

        try:
            level = log.level(record.levelname).name
        except ValueError:
            level = record.levelno

        import sys

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        log.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


@beartype
def setup_custom_hydra_logging(hydra_config: DictConfig) -> None:
    """Setup custom logging with hydra, loguru and rich, logging to hydras output directory and console.

    Args:
        hydra_config (DictConfig): Hydra config object.
    """

    hydra_internal_config = HydraConfig.get()

    log_level = "DEBUG" if hydra_config.get("debug") else "INFO"
    log.configure(
        handlers=[
            {
                "sink": RichHandler(level="DEBUG", log_time_format="%Y-%m-%d %H:%M:%S", show_path=True),
                "format": "{message}",
                "level": log_level,
            },
            {
                "sink": f"{hydra_internal_config.runtime.output_dir}/{hydra_internal_config.job.name}.log",
                "format": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line}\t| {message}",
                "level": log_level,
            },
        ],
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


@beartype
def disable_logging_groups(logging_groups: str | list[str]) -> None:
    """Disable logging for specific groups.

    Args:
        loggin_groups (list[str]): List of groups to disable logging for.
    """

    if isinstance(logging_groups, str):
        logging_groups = [logging_groups]

    for group in logging_groups:
        log.disable(group)
