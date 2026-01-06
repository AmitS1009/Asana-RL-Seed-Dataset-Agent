from __future__ import annotations

from dataclasses import dataclass
import os


def _get_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    return int(v)


def _get_str(name: str, default: str) -> str:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    return v


def _get_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Config:
    seed: int
    db_path: str
    history_days: int

    target_users: int
    teams_count: int
    projects_count: int
    avg_tasks_per_project: int

    use_llm_text: bool

    groq_api_key: str
    groq_model: str
    groq_max_calls: int

    enable_web_scrape: bool


def load_config() -> Config:
    return Config(
        seed=_get_int("SEED", 1337),
        db_path=_get_str("DB_PATH", "output/asana_simulation.sqlite"),
        history_days=_get_int("HISTORY_DAYS", 180),
        target_users=_get_int("TARGET_USERS", 7000),
        teams_count=_get_int("TEAMS_COUNT", 80),
        projects_count=_get_int("PROJECTS_COUNT", 240),
        avg_tasks_per_project=_get_int("AVG_TASKS_PER_PROJECT", 260),
        use_llm_text=_get_bool("USE_LLM_TEXT", False),
        groq_api_key=_get_str("GROQ_API_KEY", ""),
        groq_model=_get_str("GROQ_MODEL", "llama-3.1-70b-versatile"),
        groq_max_calls=_get_int("GROQ_MAX_CALLS", 40),
        enable_web_scrape=_get_bool("ENABLE_WEB_SCRAPE", False),
    )
