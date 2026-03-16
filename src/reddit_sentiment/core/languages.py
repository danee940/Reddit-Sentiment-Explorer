from __future__ import annotations

from typing import Final

DEFAULT_CONTENT_LANGUAGE: Final[str] = "hu"
SUPPORTED_UI_LANGUAGES: Final[tuple[str, ...]] = ("en", "hu")
COMMON_CONTENT_LANGUAGE_OPTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("ar", "Arabic"),
    ("bn", "Bengali"),
    ("de", "German"),
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("hi", "Hindi"),
    ("hu", "Hungarian"),
    ("id", "Indonesian"),
    ("it", "Italian"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("nl", "Dutch"),
    ("pl", "Polish"),
    ("pt", "Portuguese"),
    ("ro", "Romanian"),
    ("ru", "Russian"),
    ("th", "Thai"),
    ("tr", "Turkish"),
    ("uk", "Ukrainian"),
    ("vi", "Vietnamese"),
    ("zh", "Chinese"),
)
SUPPORTED_CONTENT_LANGUAGES: Final[frozenset[str]] = frozenset(
    code for code, _ in COMMON_CONTENT_LANGUAGE_OPTIONS
)
LANGUAGE_LABELS_BY_CODE: Final[dict[str, str]] = dict(COMMON_CONTENT_LANGUAGE_OPTIONS)


def normalize_ui_language(value: str | None) -> str:
    if not value:
        return "en"
    base_value = value.lower().replace("_", "-").split("-", maxsplit=1)[0]
    return base_value if base_value in SUPPORTED_UI_LANGUAGES else "en"


def normalize_content_language(value: str | None) -> str:
    if not value:
        return DEFAULT_CONTENT_LANGUAGE
    base_value = value.lower().replace("_", "-").split("-", maxsplit=1)[0]
    return base_value if base_value in SUPPORTED_CONTENT_LANGUAGES else DEFAULT_CONTENT_LANGUAGE


def normalize_detected_language(value: str | None) -> str | None:
    if not value:
        return None
    return value.lower().replace("_", "-").split("-", maxsplit=1)[0]


def get_content_language_options() -> list[dict[str, str]]:
    return [{"label": label, "value": code} for code, label in COMMON_CONTENT_LANGUAGE_OPTIONS]


def get_language_label(code: str | None) -> str:
    normalized_code = normalize_content_language(code)
    return LANGUAGE_LABELS_BY_CODE.get(normalized_code, normalized_code.upper())
