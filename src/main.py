import logging
import os
import signal
import time

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

_running = True


def _handle_signal(signum: int, _frame: object) -> None:
    global _running
    logger.info("Received signal %s — shutting down", signum)
    _running = False


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info("Toy app starting — APP_ENV=%s", os.getenv("APP_ENV", "development"))
    logger.info("Ready. Replace this placeholder with your web framework (FastAPI, Flask, etc.)")

    while _running:
        time.sleep(1)

    logger.info("Toy app stopped.")


if __name__ == "__main__":
    main()
