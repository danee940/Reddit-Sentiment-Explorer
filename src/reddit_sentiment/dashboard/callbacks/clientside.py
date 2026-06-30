from __future__ import annotations

from dash import Dash, Input, Output, State

THEME_RESOLVE_SCRIPT = """
function(currentTheme, _) {
    const resolvedTheme = ["light", "dark"].includes(currentTheme)
        ? currentTheme
        : (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.style.colorScheme = resolvedTheme;
    document.body.classList.toggle("theme-dark", resolvedTheme === "dark");
    document.body.classList.toggle("theme-light", resolvedTheme === "light");
    return [resolvedTheme, "theme-shell theme-" + resolvedTheme + " min-h-screen"];
}
"""

LANGUAGE_SYNC_SCRIPT = """
function(_, currentLanguage) {
    const supportedLanguages = ["en", "hu"];
    const normalizeLanguage = (value) => {
        if (!value) {
            return "hu";
        }
        const baseLanguage = String(value).toLowerCase().replace("_", "-").split("-", 1)[0];
        return supportedLanguages.includes(baseLanguage) ? baseLanguage : "hu";
    };
    if (currentLanguage && supportedLanguages.includes(currentLanguage)) {
        return currentLanguage;
    }
    const browserLanguage = (navigator.languages && navigator.languages.length > 0)
        ? navigator.languages[0]
        : (navigator.language || navigator.userLanguage || "hu");
    return normalizeLanguage(browserLanguage);
}
"""

THEME_SYNC_SCRIPT = """
function(_, currentTheme) {
    if (currentTheme === "light" || currentTheme === "dark") {
        return currentTheme;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
"""


def register(app: Dash) -> None:
    app.clientside_callback(
        THEME_RESOLVE_SCRIPT,
        Output("resolved-theme-store", "data"),
        Output("app-shell", "className"),
        Input("theme-store", "data"),
        Input("theme-sync-interval", "n_intervals"),
    )

    app.clientside_callback(
        LANGUAGE_SYNC_SCRIPT,
        Output("language-store", "data"),
        Input("language-sync-interval", "n_intervals"),
        State("language-store", "data"),
    )

    app.clientside_callback(
        THEME_SYNC_SCRIPT,
        Output("theme-store", "data"),
        Input("theme-sync-interval", "n_intervals"),
        State("theme-store", "data"),
    )
