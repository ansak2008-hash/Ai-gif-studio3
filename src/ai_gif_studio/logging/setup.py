import logging


def configure_logging(level: str) -> None:
    """Configure process-wide logging once at the application boundary."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
