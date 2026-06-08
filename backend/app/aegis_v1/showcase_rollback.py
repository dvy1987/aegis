from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from app.aegis_v1.drafter_client import PROMPT_DIR, get_active_drafter_prompt_version
from app.aegis_v1.showcase_ledger import LedgerStore, default_ledger_dir, open_ledger_store
from app.aegis_v1.tools import PLAYBOOK_DIR
from app.learning.fs_store import _playbook_path
from app.learning.models import Candidate


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class FileSnapshot(BaseModel):
    path: str
    exists: bool
    content: str | None = None
    sha256: str | None = None


class PromotionStackEntry(BaseModel):
    run_type: str
    session_id: str
    promoted_at: str = Field(default_factory=_now)
    candidate_id: str
    files: list[FileSnapshot] = Field(default_factory=list)


class PromotionStack:
    def __init__(
        self,
        *,
        ledger_dir: Path | None = None,
        store: LedgerStore | None = None,
        prompts_dir: Path | None = None,
        playbooks_dir: Path | None = None,
    ) -> None:
        self.ledger_dir = ledger_dir or default_ledger_dir()
        self.store = store or open_ledger_store(ledger_dir=self.ledger_dir)
        self.store.ensure_ready()
        self.prompts_dir = prompts_dir or PROMPT_DIR
        self.playbooks_dir = playbooks_dir or PLAYBOOK_DIR
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.playbooks_dir.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self.ledger_dir / "promotion_stack.json"

    @property
    def _stack_key(self) -> str:
        return "promotion_stack.json"

    def push_checkpoint(
        self,
        *,
        run_type: str,
        session_id: str,
        candidate: Candidate,
    ) -> PromotionStackEntry:
        files = self._files_touched_by(candidate)
        entry = PromotionStackEntry(
            run_type=run_type,
            session_id=session_id,
            candidate_id=candidate.candidate_id,
            files=[self._snapshot(path) for path in files],
        )
        stack = self._read_stack()
        stack.append(entry)
        self._write_stack(stack)
        return entry

    def rollback_target(self) -> PromotionStackEntry | None:
        stack = self._read_stack()
        return stack[-1] if stack else None

    def rollback_latest(self) -> PromotionStackEntry:
        stack = self._read_stack()
        if not stack:
            raise ValueError("no promotion checkpoint available")
        entry = stack.pop()
        for snapshot in entry.files:
            path = Path(snapshot.path)
            if snapshot.exists:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(snapshot.content or "", encoding="utf-8")
            elif path.exists():
                path.unlink()
        self._write_stack(stack)
        return entry

    def _files_touched_by(self, candidate: Candidate) -> list[Path]:
        files: list[Path] = []
        for comp in candidate.components.values():
            if comp.kind == "prompt" and comp.component_id == "drafter_system_prompt":
                active_version = get_active_drafter_prompt_version()
                files.append(self.prompts_dir / "active_drafter_prompt.txt")
                files.append(self.prompts_dir / f"{active_version}.md")
            elif comp.kind == "playbook":
                files.append(_playbook_path(self.playbooks_dir, comp.component_id))
        unique: list[Path] = []
        seen: set[Path] = set()
        for path in files:
            if path not in seen:
                unique.append(path)
                seen.add(path)
        return unique

    def _snapshot(self, path: Path) -> FileSnapshot:
        if not path.exists():
            return FileSnapshot(path=str(path), exists=False)
        content = path.read_text(encoding="utf-8")
        return FileSnapshot(
            path=str(path),
            exists=True,
            content=content,
            sha256=_sha256(content),
        )

    def _read_stack(self) -> list[PromotionStackEntry]:
        if not self.store.exists(self._stack_key):
            return []
        raw = json.loads(self.store.read_text(self._stack_key))
        return [PromotionStackEntry.model_validate(item) for item in raw]

    def _write_stack(self, stack: list[PromotionStackEntry]) -> None:
        self.store.write_text(
            self._stack_key,
            json.dumps([entry.model_dump() for entry in stack], indent=2),
        )
