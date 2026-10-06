import uvicorn

from seomind.config import settings


def main() -> None:
    settings.ensure_directories()
    uvicorn.run(
        "seomind.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
