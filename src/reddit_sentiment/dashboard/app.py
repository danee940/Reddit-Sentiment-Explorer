from pathlib import Path

from dash import Dash

from reddit_sentiment.dashboard.callbacks import register_callbacks
from reddit_sentiment.dashboard.components import build_app_layout
from reddit_sentiment.dashboard.constants import FONT_URL, TAILWIND_URL

app = Dash(
    __name__,
    external_stylesheets=[FONT_URL, TAILWIND_URL],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True,
    assets_folder=str(Path(__file__).resolve().parent / "assets"),
    update_title=None,  # type: ignore[arg-type]
)
app.title = "Reddit Sentiment Explorer"

app.layout = build_app_layout()
register_callbacks(app)


server = app.server
