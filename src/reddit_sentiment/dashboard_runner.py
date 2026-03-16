import os

from reddit_sentiment.core.config import get_settings
from reddit_sentiment.dashboard.app import app


def main() -> None:
    settings = get_settings()
    debug = os.getenv("DASHBOARD_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
    app.run(
        host=settings.dashboard_host,
        port=settings.dashboard_port,
        debug=debug,
        dev_tools_hot_reload=debug,
    )


if __name__ == "__main__":
    main()
