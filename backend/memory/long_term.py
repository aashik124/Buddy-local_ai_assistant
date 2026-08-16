import json

from backend.config import MEMORY_DIR

PROFILE_PATH = MEMORY_DIR / "profile.json"


def load_profile() -> dict:
    if not PROFILE_PATH.exists():
        return {"name": "", "facts": [], "preferences": [], "projects": [], "skills": []}
    try:
        return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"name": "", "facts": [], "preferences": [], "projects": [], "skills": []}


def save_profile(profile: dict) -> None:
    PROFILE_PATH.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


def remember_fact(fact: str) -> dict:
    profile = load_profile()
    facts = profile.setdefault("facts", [])
    if fact and fact not in facts:
        facts.append(fact)
    save_profile(profile)
    return profile


def forget_profile() -> None:
    save_profile({"name": "", "facts": [], "preferences": [], "projects": [], "skills": []})
