"""Load the YAML knowledge base + Markdown prompts from disk.

This module is the single source of truth for filesystem paths. Tools should
not read files directly — they ask for a parsed rule set, a terminology map,
or a named prompt by id and let this loader handle paths and caching.
"""
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_KB_DIR = _REPO_ROOT / "knowledge_base"
_PROMPTS_DIR = _REPO_ROOT / "prompts"


@lru_cache(maxsize=1)
def load_care_gap_rules() -> dict[str, Any]:
    """Return the parsed care_gap_rules.yaml document."""
    with (_KB_DIR / "care_gap_rules.yaml").open() as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def load_terminology() -> dict[str, Any]:
    """Return the parsed terminology.yaml document."""
    with (_KB_DIR / "terminology.yaml").open() as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    """Return the contents of prompts/<name>.md."""
    return (_PROMPTS_DIR / f"{name}.md").read_text()


def get_code_set(name: str) -> dict[str, Any]:
    """Return one terminology entry by name. Raises KeyError if unknown."""
    term = load_terminology()
    if name not in term:
        raise KeyError(f"Unknown code set: {name!r}. Add it to terminology.yaml.")
    return term[name]


def label_for(category: str, code: str) -> str | None:
    """Return the friendly label for a code from terminology.labels.<category>."""
    labels = (load_terminology().get("labels") or {}).get(category, {})
    return labels.get(code)


def matches_code_set(coding: dict, code_set_name: str) -> bool:
    """Return True if a FHIR coding dict belongs to the named code set.

    A coding is {"system": "...", "code": "..."}; the code set defines a system,
    a match mode (exact|prefix), and a list of codes.
    """
    cs = get_code_set(code_set_name)
    if coding.get("system") != cs["system"]:
        return False
    code = str(coding.get("code") or "")
    if not code:
        return False
    if cs["match"] == "exact":
        return code in cs["codes"]
    if cs["match"] == "prefix":
        return any(code.startswith(p) for p in cs["codes"])
    return False
