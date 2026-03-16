from __future__ import annotations

from datetime import UTC, datetime

from reddit_sentiment.core.enums import QueryRunStatus
from reddit_sentiment.core.languages import normalize_ui_language

SENTIMENT_TRANSLATIONS = {
    "en": {
        "very_negative": "very negative",
        "negative": "negative",
        "neutral": "neutral",
        "positive": "positive",
        "very_positive": "very positive",
        "unscored": "unscored",
    },
    "hu": {
        "very_negative": "nagyon negatív",
        "negative": "negatív",
        "neutral": "semleges",
        "positive": "pozitív",
        "very_positive": "nagyon pozitív",
        "unscored": "nincs értékelve",
    },
}

SOURCE_TRANSLATIONS = {
    "en": {"post": "post", "comment": "comment", "unknown": "unknown"},
    "hu": {"post": "bejegyzés", "comment": "hozzászólás", "unknown": "ismeretlen"},
}

TRANSLATIONS = {
    "en": {
        "recent_search": "Recent search",
        "stored": "Stored",
        "status_completed": "Completed",
        "status_failed": "Failed",
        "status_pending": "Pending",
        "status_running": "Running",
        "query_completed": "Query completed.",
        "query_failed": "Query failed: {error}",
        "unknown_error": "Unknown error",
        "status_prefix": "Status: {status}",
        "date": "Date",
        "subreddit": "Subreddit",
        "sentiment": "Sentiment",
        "snippet": "Snippet",
        "unknown_date": "Unknown date",
        "select_a_match": "Select a match",
        "select_a_match_description": "Pick a result from the list to inspect the full matched content and metadata.",
        "source": "Source",
        "score": "Score",
        "matched_content": "Matched content",
        "rationale": "Rationale",
        "evidence_phrases": "Evidence phrases",
        "no_evidence_phrases": "No evidence phrases available.",
        "no_content_available": "No content available.",
        "open_on_reddit": "Open on Reddit",
        "no_permalink_available": "No permalink available",
        "configuration": "Configuration",
        "subreddit_scope_title": "Subreddit Scope",
        "subreddit_scope_description": "Choose where the next query will search. Leave the list empty to fall back to the default env configuration.",
        "add_subreddit_names": "Add subreddit names",
        "add_subreddits": "Add subreddits",
        "subreddit_help_text": "Use commas to add multiple subreddits. Current defaults: {defaults}.",
        "search_scope": "Search Scope",
        "search_scope_description": "Each subreddit is validated before the query runs so you can spot broken entries early.",
        "theme": "Theme",
        "theme_description": "Use your system setting by default or override it manually.",
        "theme_system": "System",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "language": "Language",
        "language_description": "Detect your browser language automatically and let you override it manually.",
        "language_en": "English",
        "language_hu": "Magyar",
        "language_short_en": "EN",
        "language_short_hu": "HU",
        "content_language": "Search language",
        "content_language_description": "Choose the language of the Reddit content to analyze.",
        "hero_badge": "Reddit Sentiment Explorer",
        "hero_title": "A sharper, cleaner command center for multilingual Reddit sentiment.",
        "hero_description": "Choose a content language, manage subreddit scope, and explore trends, sentiment, and matched content in one place.",
        "run_a_search": "Run a search",
        "enter_search_term": "Enter a search term",
        "search": "Search",
        "tab_subreddit_scope": "Subreddit Scope",
        "tab_search_overview": "Search And Overview",
        "tab_sentiment_trends": "Sentiment Trends",
        "tab_subreddit_breakdown": "Subreddit Breakdown",
        "tab_matched_content": "Matched Content Explorer",
        "enter_at_least_one_subreddit": "Enter at least one subreddit.",
        "already_added": "Already added: {subreddits}.",
        "added": "Added: {subreddits}.",
        "skipped_duplicates": "Skipped duplicates: {subreddits}.",
        "removed_subreddit": "Removed r/{subreddit}.",
        "using_env_defaults": "Using env defaults",
        "subreddit_validation_unavailable": "Subreddit validation is currently unavailable.",
        "custom_subreddit_scope": "Custom subreddit scope",
        "exists": "Exists",
        "not_found": "Not found",
        "checking": "Checking",
        "remove": "Remove",
        "no_recent_searches": "No recent searches yet.",
        "untitled_search": "Untitled search",
        "recent_searches": "Recent searches",
        "enter_search_term_message": "Enter a search term.",
        "error_prefix": "Error: {error}",
        "query_started": "Query started: {query_run_id}",
        "no_active_query": "No active query.",
        "no_data_yet": "No data yet",
        "matched_content_will_appear": "Matched content will appear here.",
        "run_search_to_inspect": "Run a search to inspect the Reddit posts and comments that matched your query.",
        "overview": "Overview",
        "overview_empty_title": "Search insights appear here after your first run.",
        "overview_empty_description": "Use the Subreddit Scope tab to tune the data source, then run a search to populate charts and document exploration.",
        "tracked_subreddits": "Tracked subreddits",
        "result_status": "Result status",
        "waiting": "Waiting",
        "documents": "Documents",
        "results_when_complete": "Results will appear when the run completes",
        "search_still_running": "Search is still running.",
        "search_still_running_description": "The charts and matched content explorer will populate automatically after processing finishes.",
        "search_in_progress": "Search in progress",
        "search_in_progress_description": "The current run is being processed. Results will refresh automatically when they are ready.",
        "query": "Query",
        "status": "Status",
        "subreddits": "Subreddits",
        "current_run": "Current run",
        "search_overview": "Search overview",
        "search_overview_description": "A quick read of the current run, including document volume and average sentiment.",
        "average_score": "Average score",
        "sentiment_distribution": "Sentiment distribution",
        "no_distribution_data": "No distribution data",
        "sentiment_over_time": "Sentiment over time",
        "no_timeline_data": "No timeline data",
        "volume_over_time": "Volume over time",
        "no_volume_data": "No volume data",
        "subreddit_breakdown": "Subreddit breakdown",
        "no_subreddit_data": "No subreddit data",
        "documents_eyebrow": "Documents",
        "matched_content_explorer": "Matched content explorer",
        "documents_description": "Scan matches quickly, then inspect one selected document in detail.",
        "filter_by_subreddit": "Filter by subreddit",
        "filter_by_date": "Filter by date",
        "filter_by_sentiment": "Filter by sentiment",
        "filter_by_source": "Filter by source",
        "search_snippet_text": "Search snippet text",
        "chart_axis_date": "Date",
        "chart_axis_average_score": "Average sentiment score",
        "chart_axis_document_count": "Document count",
        "chart_axis_match_count": "Matches",
        "chart_axis_subreddit": "Subreddit",
        "chart_hover_average_score": "Average score",
        "chart_hover_document_count": "Documents",
        "chart_hover_match_count": "Matches",
        "clear_filters": "Clear filters",
        "rolling_sentiment": "Rolling sentiment trend",
        "no_rolling_sentiment_data": "No rolling trend data",
        "sentiment_heatmap": "Sentiment heatmap",
        "no_heatmap_data": "No heatmap data",
        "chart_axis_subreddit_date": "Subreddit by date",
        "chart_axis_average_sentiment": "Average sentiment",
        "phrase_breakdown": "Phrase drivers",
        "phrase_breakdown_description": "Grounded evidence phrases that appear most often inside each sentiment bucket.",
        "no_phrase_breakdown": "No phrase breakdown available yet.",
        "spike_analysis": "Spike analysis",
        "spike_analysis_description": "High-volume days and sharp sentiment swings worth inspecting first.",
        "no_spike_events": "No major spikes detected.",
        "score_change": "Score change",
        "confidence_high": "Higher-confidence documents",
        "confidence_low": "Lower-confidence documents",
        "sentiment_confidence": "Sentiment confidence",
    },
    "hu": {
        "recent_search": "Legutóbbi keresés",
        "stored": "Tárolva",
        "status_completed": "Befejezve",
        "status_failed": "Sikertelen",
        "status_pending": "Függőben",
        "status_running": "Folyamatban",
        "query_completed": "A lekérdezés befejeződött.",
        "query_failed": "A lekérdezés sikertelen: {error}",
        "unknown_error": "Ismeretlen hiba",
        "status_prefix": "Állapot: {status}",
        "date": "Dátum",
        "subreddit": "Subreddit",
        "sentiment": "Érzelem",
        "snippet": "Részlet",
        "unknown_date": "Ismeretlen dátum",
        "select_a_match": "Válassz egy találatot",
        "select_a_match_description": "Válassz egy elemet a listából a teljes egyező tartalom és a metaadatok megtekintéséhez.",
        "source": "Forrás",
        "score": "Pontszám",
        "matched_content": "Egyező tartalom",
        "rationale": "Indoklás",
        "evidence_phrases": "Bizonyító kifejezések",
        "no_evidence_phrases": "Nincsenek elérhető bizonyító kifejezések.",
        "no_content_available": "Nincs elérhető tartalom.",
        "open_on_reddit": "Megnyitás Redditen",
        "no_permalink_available": "Nincs elérhető permalink",
        "configuration": "Beállítás",
        "subreddit_scope_title": "Subreddit hatókör",
        "subreddit_scope_description": "Válaszd ki, hogy a következő lekérdezés hol keressen. Hagyd üresen a listát az alapértelmezett env konfiguráció használatához.",
        "add_subreddit_names": "Subreddit nevek hozzáadása",
        "add_subreddits": "Subredditek hozzáadása",
        "subreddit_help_text": "Több subreddit hozzáadásához vesszőt használj. Jelenlegi alapértelmezettek: {defaults}.",
        "search_scope": "Keresési hatókör",
        "search_scope_description": "Minden subreddit ellenőrzött a lekérdezés indítása előtt, így hamar kiderülnek a hibás elemek.",
        "theme": "Téma",
        "theme_description": "Alapból a rendszerbeállítást használja, de manuálisan is felülírhatod.",
        "theme_system": "Rendszer",
        "theme_light": "Világos",
        "theme_dark": "Sötét",
        "language": "Nyelv",
        "language_description": "Automatikusan felismeri a böngésző nyelvét, és kézzel is bármikor átváltható.",
        "language_en": "English",
        "language_hu": "Magyar",
        "language_short_en": "EN",
        "language_short_hu": "HU",
        "content_language": "Érzelemelemzés nyelve",
        "content_language_description": "Válaszd ki a Reddit-tartalom nyelvét, amelyet az érzelmi elemzéshez használj.",
        "hero_badge": "Reddit Sentiment Explorer",
        "hero_title": "Élesebb, tisztább irányítópult a többnyelvű Reddit-érzelemelemzéshez.",
        "hero_description": "Válassz tartalmi nyelvet, kezeld a subreddit hatókört, és egy helyen fedezd fel a trendeket, érzelmeket és az egyező tartalmakat.",
        "run_a_search": "Keresés indítása",
        "enter_search_term": "Adj meg egy keresési kifejezést",
        "search": "Keresés",
        "tab_subreddit_scope": "Subreddit hatókör",
        "tab_search_overview": "Keresés és áttekintés",
        "tab_sentiment_trends": "Érzelmi trendek",
        "tab_subreddit_breakdown": "Subreddit bontás",
        "tab_matched_content": "Egyező tartalom nézet",
        "enter_at_least_one_subreddit": "Adj meg legalább egy subredditet.",
        "already_added": "Már hozzáadva: {subreddits}.",
        "added": "Hozzáadva: {subreddits}.",
        "skipped_duplicates": "Duplikátum kihagyva: {subreddits}.",
        "removed_subreddit": "Eltávolítva: r/{subreddit}.",
        "using_env_defaults": "Env alapértelmezettek használata",
        "subreddit_validation_unavailable": "A subreddit ellenőrzés jelenleg nem érhető el.",
        "custom_subreddit_scope": "Egyedi subreddit hatókör",
        "exists": "Létezik",
        "not_found": "Nem található",
        "checking": "Ellenőrzés",
        "remove": "Eltávolítás",
        "no_recent_searches": "Meg nincsenek friss keresések.",
        "untitled_search": "Névtelen keresés",
        "recent_searches": "Legutóbbi keresések",
        "enter_search_term_message": "Adj meg egy keresési kifejezést.",
        "error_prefix": "Hiba: {error}",
        "query_started": "Lekérdezés elindítva: {query_run_id}",
        "no_active_query": "Nincs aktív lekérdezés.",
        "no_data_yet": "Még nincs adat",
        "matched_content_will_appear": "Az egyező tartalom itt fog megjelenni.",
        "run_search_to_inspect": "Indíts egy keresést a lekérdezésedhez illő Reddit bejegyzések és hozzászólások megtekintéséhez.",
        "overview": "Áttekintés",
        "overview_empty_title": "A keresési eredmények az első futás után jelennek meg itt.",
        "overview_empty_description": "A Subreddit hatókör fülön hangolhatod az adatforrást, majd egy kereséssel feltöltheted a diagramokat és a dokumentumnézetet.",
        "tracked_subreddits": "Követett subredditek",
        "result_status": "Eredmény állapota",
        "waiting": "Várakozás",
        "documents": "Dokumentumok",
        "results_when_complete": "Az eredmények a futás befejezése után jelennek meg",
        "search_still_running": "A keresés még fut.",
        "search_still_running_description": "A diagramok és az egyező tartalom nézet automatikusan feltöltődik, amikor a feldolgozás befejeződik.",
        "search_in_progress": "Keresés folyamatban",
        "search_in_progress_description": "Az aktuális futás feldolgozás alatt áll. Az eredmények automatikusan frissülnek, amikor elkészülnek.",
        "query": "Lekérdezés",
        "status": "Állapot",
        "subreddits": "Subredditek",
        "current_run": "Aktuális futás",
        "search_overview": "Keresési áttekintés",
        "search_overview_description": "Gyors összefoglaló az aktuális futásról, beleértve a dokumentummennyiséget és az átlagos érzelmi pontszámot.",
        "average_score": "Átlagos pontszám",
        "sentiment_distribution": "Érzelmi megoszlás",
        "no_distribution_data": "Nincs megoszlási adat",
        "sentiment_over_time": "Érzelem időben",
        "no_timeline_data": "Nincs idősoros adat",
        "volume_over_time": "Mennyiség időben",
        "no_volume_data": "Nincs mennyiségi adat",
        "subreddit_breakdown": "Subreddit bontás",
        "no_subreddit_data": "Nincs subreddit adat",
        "documents_eyebrow": "Dokumentumok",
        "matched_content_explorer": "Egyező tartalom nézet",
        "documents_description": "Gyorsan nézd át a találatokat, majd vizsgáld meg részletesen a kiválasztott dokumentumot.",
        "filter_by_subreddit": "Szűrés subreddit szerint",
        "filter_by_date": "Szűrés dátum szerint",
        "filter_by_sentiment": "Szűrés érzelem szerint",
        "filter_by_source": "Szűrés forrás szerint",
        "search_snippet_text": "Keresés a részlet szövegében",
        "chart_axis_date": "Dátum",
        "chart_axis_average_score": "Átlagos érzelmi pontszám",
        "chart_axis_document_count": "Dokumentumok száma",
        "chart_axis_match_count": "Találatok",
        "chart_axis_subreddit": "Subreddit",
        "chart_hover_average_score": "Átlagos pontszám",
        "chart_hover_document_count": "Dokumentumok",
        "chart_hover_match_count": "Találatok",
        "clear_filters": "Szűrők törlése",
        "rolling_sentiment": "Gördülő érzelmi trend",
        "no_rolling_sentiment_data": "Nincs gördülő trend adat",
        "sentiment_heatmap": "Érzelmi hőtérkép",
        "no_heatmap_data": "Nincs hőtérkép adat",
        "chart_axis_subreddit_date": "Subreddit és dátum",
        "chart_axis_average_sentiment": "Átlagos érzelem",
        "phrase_breakdown": "Kifejezés minták",
        "phrase_breakdown_description": "Az egyes érzelmi kategóriákhoz leggyakrabban kapcsolódó, szövegből vett bizonyító kifejezések.",
        "no_phrase_breakdown": "Még nincs elérhető kifejezés bontás.",
        "spike_analysis": "Kiugrás elemzés",
        "spike_analysis_description": "Azok a napok, ahol nagyobb volt a forgalom vagy hirtelen elmozdult az érzelem.",
        "no_spike_events": "Nem találhatók jelentős kiugrások.",
        "score_change": "Pontszám változás",
        "confidence_high": "Magasabb megbízhatóságú dokumentumok",
        "confidence_low": "Alacsonyabb megbízhatóságú dokumentumok",
        "sentiment_confidence": "Érzelem besoro\u00adlás megbízha\u00adtósága",
    },
}


def normalize_language(value: str | None) -> str:
    return normalize_ui_language(value)


def t(language: str | None, key: str, **kwargs) -> str:
    normalized_language = normalize_language(language)
    template = TRANSLATIONS[normalized_language].get(key) or TRANSLATIONS["en"][key]
    return template.format(**kwargs)


def translate_sentiment_label(label: str | None, language: str | None) -> str:
    normalized_language = normalize_language(language)
    sentiment_label = label or "unscored"
    return SENTIMENT_TRANSLATIONS[normalized_language].get(
        sentiment_label,
        sentiment_label.replace("_", " "),
    )


def translate_source_label(source_type: str | None, language: str | None) -> str:
    normalized_language = normalize_language(language)
    source_label = (source_type or "unknown").lower()
    return SOURCE_TRANSLATIONS[normalized_language].get(
        source_label,
        source_label.replace("_", " "),
    )


def translate_status_label(status: str | None, language: str | None) -> str:
    if status == QueryRunStatus.completed.value:
        return t(language, "status_completed")
    if status == QueryRunStatus.failed.value:
        return t(language, "status_failed")
    if status == QueryRunStatus.pending.value:
        return t(language, "status_pending")
    if status == QueryRunStatus.running.value:
        return t(language, "status_running")
    if status:
        return status.replace("_", " ").title()
    return t(language, "stored")


def format_selected_subreddit_count(language: str | None, count: int) -> str:
    if normalize_language(language) == "hu":
        return f"{count} subreddit kiválasztva"
    return f"{count} subreddit{'s' if count != 1 else ''} selected"


def format_matches_summary(language: str | None, match_count: int, subreddit_count: int) -> str:
    if normalize_language(language) == "hu":
        return f"{match_count} találat {subreddit_count} subredditben"
    return (
        f"{match_count} match{'es' if match_count != 1 else ''}"
        f" across {subreddit_count} subreddit{'s' if subreddit_count != 1 else ''}"
    )


def format_history_time(value: str | None, language: str | None) -> str:
    if not value:
        return t(language, "recent_search")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return t(language, "recent_search")
    return parsed.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def build_history_status(status: str | None, language: str | None) -> str:
    return translate_status_label(status, language)


def build_status_message(store_data: dict | None, language: str | None) -> str:
    if not store_data:
        return ""
    status = store_data.get("status")
    if status == QueryRunStatus.completed.value:
        return t(language, "query_completed")
    if status == QueryRunStatus.failed.value:
        return t(
            language,
            "query_failed",
            error=store_data.get("error_message", t(language, "unknown_error")),
        )
    return t(language, "status_prefix", status=build_history_status(status, language))
