import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# Path resolution from backend/app/services/plugin_context.py:
# parents[0] = backend/app/services/
# parents[1] = backend/app/
# parents[2] = backend/           ← plugins/ lives here ✅
# parents[3] = project root       ← wrong
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


_sop_cache = None


def build_team_sop(max_chars=12000):
    """Load agent personas and skill SOPs from the plugin directory into a single context string."""
    global _sop_cache
    # Only use cache if it has actual content — empty string means previous load failed
    # (e.g. wrong path was used). We retry until content is found.
    if _sop_cache:
        return _sop_cache
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
    else:
        logger.warning(f"[PluginContext] agents_dir not found: {agents_dir}")
    if skills_dir.exists():
        for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
            content = _read_file(skill_file)
            if content:
                parts.append(f"### SKILL: {skill_file.parent.name}\n{content}")
    else:
        logger.warning(f"[PluginContext] skills_dir not found: {skills_dir}")
    if not parts:
        logger.error(f"[PluginContext] No agent/skill content loaded — check PLUGIN_DIR: {_PLUGIN_DIR}")
        _sop_cache = ""
        return _sop_cache
    sop = "\n\n".join(parts)
    if len(sop) > max_chars:
        sop = sop[:max_chars]
    logger.info(f"[PluginContext] Loaded {len(parts)} agent/skill docs, {len(sop)} chars of SOP context.")
    _sop_cache = sop
    return _sop_cache

