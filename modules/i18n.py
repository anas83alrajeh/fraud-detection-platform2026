"""
i18n.py
------------------------------------------------------------------
Internationalization layer for the Fraud & Anomaly Detection Platform.

- Loads JSON locale files from /locales (ar, en, de).
- Provides a translate helper `t("section.key", **fmt)`.
- Tracks the active language in st.session_state.
- Exposes direction (rtl/ltr) and font per language.

All processing is local. No external services are used.
"""

import json
import os
from functools import lru_cache

import streamlit as st

# Languages available in the app. The order here controls the dropdown order.
SUPPORTED_LANGUAGES = ["ar", "en", "de"]
DEFAULT_LANGUAGE = "ar"

_LOCALES_DIR = os.path.join(os.path.dirname(__file__), "..", "locales")


@lru_cache(maxsize=None)
def _load_locale(lang: str) -> dict:
    """Read and cache a single locale JSON file."""
    path = os.path.normpath(os.path.join(_LOCALES_DIR, f"{lang}.json"))
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def init_language() -> None:
    """Ensure a language is set in the session state."""
    if "lang" not in st.session_state:
        st.session_state["lang"] = DEFAULT_LANGUAGE


def get_lang() -> str:
    """Return the active language code."""
    return st.session_state.get("lang", DEFAULT_LANGUAGE)


def set_lang(lang: str) -> None:
    """Switch the active language."""
    if lang in SUPPORTED_LANGUAGES:
        st.session_state["lang"] = lang


def get_direction(lang: str | None = None) -> str:
    """Return 'rtl' for Arabic, 'ltr' otherwise."""
    lang = lang or get_lang()
    return _load_locale(lang)["meta"]["direction"]


def get_font(lang: str | None = None) -> str:
    """Return the CSS font-family stack for the language."""
    lang = lang or get_lang()
    return _load_locale(lang)["meta"]["font_family"]


def language_options() -> dict:
    """Map language code -> display name (e.g. {'ar': 'العربية'})."""
    return {lang: _load_locale(lang)["meta"]["lang_name"] for lang in SUPPORTED_LANGUAGES}


def t(key: str, **fmt) -> str:
    """
    Translate a dotted key, e.g. t("price_variance.title").

    Supports {placeholder} formatting: t("sidebar.loaded_rows", n=120).
    Falls back to the key itself if the translation is missing, so the UI
    never breaks during development.
    """
    data = _load_locale(get_lang())
    node = data
    for part in key.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return key  # graceful fallback
    if isinstance(node, str) and fmt:
        try:
            return node.format(**fmt)
        except (KeyError, IndexError):
            return node
    return node
