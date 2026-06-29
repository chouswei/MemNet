"""Resolve novel application paths from --app instance or --seed markdown."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
INSTANCES_DIR = APP_DIR / "instances"
RESULT_MARKER = "NOVEL_BEAT_RESULT"
MODEL_SCRIPT = "deepseek-v4-flash"
MODEL_PROSE = "deepseek-v4-flash"

_USR14_RE = re.compile(
    r"@USR:\s*USR14\|chapter_out\|([^|\s]+)",
)
_USR15_RE = re.compile(
    r"@USR:\s*USR15\|snapshot\|([^|\s]+)",
)
_TITLE_RE = re.compile(r"^#\s+(.+)", re.MULTILINE)


def repo_root() -> Path:
    return APP_DIR.parents[1]


@dataclass(frozen=True)
class NovelAppConfig:
    app_id: str
    seed_md: Path
    title: str
    output_dir: Path
    chapter_dir: Path
    snapshot_file: Path
    session_id_file: Path
    last_beat_file: Path
    agents_dir: Path
    model_script: str = MODEL_SCRIPT
    model_prose: str = MODEL_PROSE
    thinking_script: bool = False
    thinking_prose: bool = False
    expand_catalog: bool = False
    expand_catalog_target: int = 80
    expand_catalog_seed: int | None = None
    catalog_schema: Path | None = None

    @property
    def catalog_store_dir(self) -> Path | None:
        if not self.catalog_schema:
            return None
        return repo_root() / "novel-output" / "catalogs" / self.catalog_schema.stem

    @property
    def catalog_session_id_file(self) -> Path | None:
        store = self.catalog_store_dir
        return store / "catalog_session_id.txt" if store else None

    @property
    def catalog_snapshot_file(self) -> Path | None:
        store = self.catalog_store_dir
        return store / "catalog_snap.json" if store else None

    @property
    def script_agent_id_file(self) -> Path:
        return self.agents_dir / "script_agent_id.txt"

    @property
    def prose_agent_id_file(self) -> Path:
        return self.agents_dir / "prose_agent_id.txt"

    @property
    def threads_dir(self) -> Path:
        return self.output_dir / "threads"

    @property
    def seed_md_rel(self) -> str:
        return str(self.seed_md.relative_to(repo_root())).replace("\\", "/")


def _parse_paths_from_seed(seed_md: Path) -> tuple[Path, Path, Path, str, str]:
    text = seed_md.read_text(encoding="utf-8")
    m15 = _USR15_RE.search(text)
    m14 = _USR14_RE.search(text)
    root = repo_root()
    if m15:
        snap = root / m15.group(1).replace("/", "\\")
        out_dir = snap.parent
    elif m14:
        ch = root / m14.group(1).replace("/", "\\")
        out_dir = ch.parent
        snap = out_dir / "session_snap.json"
    else:
        out_dir = root / "novel-output" / seed_md.stem.replace("novel-", "").replace(
            "-initial-state", ""
        )
        snap = out_dir / "session_snap.json"
    ch_dir = root / m14.group(1).replace("/", "\\") if m14 else out_dir / "chapters"
    title_m = _TITLE_RE.search(text)
    title = title_m.group(1).strip() if title_m else seed_md.stem
    app_id = out_dir.name
    return out_dir, snap, ch_dir, title, app_id


def _models_from_instance(inst: dict | None) -> tuple[str, str, bool, bool]:
    if not inst:
        return MODEL_SCRIPT, MODEL_PROSE, False, False
    script = str(inst.get("model_script") or MODEL_SCRIPT).strip()
    prose = str(inst.get("model_prose") or MODEL_PROSE).strip()
    think_script = bool(inst.get("thinking_script", False))
    think_prose = bool(inst.get("thinking_prose", False))
    return script, prose, think_script, think_prose


def _make_config(
    *,
    app_id: str,
    seed_path: Path,
    title: str,
    out_dir: Path,
    snap: Path,
    ch_dir: Path,
    inst: dict | None = None,
) -> NovelAppConfig:
    model_script, model_prose, thinking_script, thinking_prose = _models_from_instance(inst)
    expand = False
    expand_target = 80
    expand_seed: int | None = None
    catalog_schema: Path | None = None
    if inst:
        expand = bool(inst.get("expand_catalog", False))
        expand_target = int(inst.get("expand_catalog_target", 80))
        raw_seed = inst.get("expand_catalog_seed")
        expand_seed = int(raw_seed) if raw_seed is not None else None
        raw_schema = inst.get("catalog_schema")
        if raw_schema:
            schema_path = Path(str(raw_schema))
            if not schema_path.is_absolute():
                schema_path = repo_root() / schema_path
            catalog_schema = schema_path
    return NovelAppConfig(
        app_id=app_id,
        seed_md=seed_path,
        title=title,
        output_dir=out_dir,
        chapter_dir=ch_dir,
        snapshot_file=snap,
        session_id_file=out_dir / "session_id.txt",
        last_beat_file=out_dir / "last_beat.json",
        agents_dir=out_dir / "agents",
        model_script=model_script,
        model_prose=model_prose,
        thinking_script=thinking_script,
        thinking_prose=thinking_prose,
        expand_catalog=expand,
        expand_catalog_target=expand_target,
        expand_catalog_seed=expand_seed,
        catalog_schema=catalog_schema,
    )


def _load_instance_json(app_id: str) -> dict | None:
    path = INSTANCES_DIR / f"{app_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(
    *,
    app_id: str | None = None,
    seed_md: str | Path | None = None,
) -> NovelAppConfig:
    root = repo_root()
    if app_id and seed_md:
        raise ValueError("use only one of app_id or seed_md")

    if app_id:
        inst = _load_instance_json(app_id)
        if inst:
            seed_path = root / inst.get("seed_md", "")
            title = inst.get("title") or app_id
            if not seed_path.is_file():
                raise FileNotFoundError(f"seed not found: {seed_path}")
            out_dir, snap, ch_dir, parsed_title, slug = _parse_paths_from_seed(seed_path)
            return _make_config(
                app_id=inst.get("app_id", app_id),
                seed_path=seed_path,
                title=title or parsed_title,
                out_dir=out_dir,
                snap=snap,
                ch_dir=ch_dir,
                inst=inst,
            )
        seed_path = root / "application-notes" / f"novel-{app_id.replace('_', '-')}-initial-state.md"
        if not seed_path.is_file():
            raise FileNotFoundError(
                f"no instance {app_id}.json and no seed at {seed_path}"
            )
    elif seed_md:
        seed_path = Path(seed_md)
        if not seed_path.is_absolute():
            seed_path = root / seed_path
        app_id = None
    else:
        env_app = __import__("os").environ.get("NOVEL_APP", "").strip()
        if env_app:
            return load_config(app_id=env_app)
        raise ValueError("pass --app <id> or --seed <application-notes/*.md>")

    if not seed_path.is_file():
        raise FileNotFoundError(f"seed not found: {seed_path}")

    out_dir, snap, ch_dir, title, slug = _parse_paths_from_seed(seed_path)
    return _make_config(
        app_id=app_id or slug,
        seed_path=seed_path,
        title=title,
        out_dir=out_dir,
        snap=snap,
        ch_dir=ch_dir,
        inst=_load_instance_json(app_id or slug) if (app_id or slug) else None,
    )
