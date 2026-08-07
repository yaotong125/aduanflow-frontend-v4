import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_PLUGIN_DIR = Path(__file__).resolve().parents[2] / "plugins" / "dispute-automation-expert-team"
_SKIP_FILES = {"member-placeholder.md"}


def _read_file(path):
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        logger.debug(f"[PluginContext] read failed {path}: {exc}")
        return ""


@lru_cache(maxsize=1)
def build_team_sop(max_chars=12000):
    parts = []
    agents_dir = _PLUGIN_DIR / "agents"
    skills_dir = _PLUGIN_DIR / "skills"
    if agents_dir.exists():
        for md_file in sorted(agents_dir.glob("*.md")):
            if md_file.name in _SKIP_FILES:
                continue
            content = _read_file(md_file)
            if content:
                parts.append(f"### AGENT: {md_file.stem}\n{content}")
    if skills_dir.exists():
        for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
            content = _read_file(skill_file)
            if content:
                parts.append(f"### SKILL: {skill_file.parent.name}\n{content}")
    if not parts:
        return ""
    sop = "\n\n".join(parts)
    if len(sop) > max_chars:
        sop = sop[:max_chars]
    return sop
