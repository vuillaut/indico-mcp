from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

_TRUE = {"1", "true", "yes", "on"}
_NAME = re.compile(r"[a-z][a-z0-9_]*")


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUE


@dataclass(frozen=True)
class Instance:
    name: str
    url: str
    token: str | None = None

    @property
    def host(self) -> str:
        return urlsplit(self.url).hostname or ""


@dataclass(frozen=True)
class Settings:
    instances: tuple[Instance, ...]
    read_only: bool = False
    allow_delete: bool = False
    upload_dir: Path | None = None
    timeout: float = 30.0
    default: str | None = field(default=None)

    def __post_init__(self) -> None:
        if not self.instances:
            raise ValueError("at least one Indico instance is required")
        names = [i.name for i in self.instances]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate instance names: {names}")
        if self.default is not None and self.default not in names:
            raise ValueError(f"default instance {self.default!r} is not one of {names}")

    @classmethod
    def single(cls, url: str, token: str | None = None, **kwargs) -> Settings:
        """One instance, named after its host (e.g. indico.cern.ch)."""
        url = url.strip().rstrip("/")
        instance = Instance(name=urlsplit(url).hostname or url, url=url, token=token)
        return cls(instances=(instance,), **kwargs)

    @classmethod
    def from_env(cls) -> Settings:
        upload_dir = os.environ.get("INDICO_UPLOAD_DIR")
        common = {
            "read_only": _flag("INDICO_READ_ONLY"),
            "allow_delete": _flag("INDICO_ALLOW_DELETE"),
            "upload_dir": Path(upload_dir).expanduser().resolve() if upload_dir else None,
            "timeout": float(os.environ.get("INDICO_TIMEOUT", "30")),
        }
        if spec := os.environ.get("INDICO_INSTANCES", "").strip():
            try:
                return cls(
                    instances=_parse_instances(spec),
                    default=os.environ.get("INDICO_DEFAULT_INSTANCE", "").strip().lower() or None,
                    **common,
                )
            except ValueError as exc:
                raise SystemExit(f"INDICO_INSTANCES: {exc}") from exc
        url = os.environ.get("INDICO_URL", "").strip()
        if not url:
            raise SystemExit(
                "Set INDICO_URL (one instance), e.g. INDICO_URL=https://indico.cern.ch, "
                "or INDICO_INSTANCES (several), e.g. INDICO_INSTANCES=cern=https://indico.cern.ch,in2p3=https://indico.in2p3.fr"
            )
        return cls.single(url, os.environ.get("INDICO_TOKEN") or None, **common)


def _parse_instances(spec: str) -> tuple[Instance, ...]:
    """`name=url,name=url`; each token comes from INDICO_TOKEN_<NAME>."""
    instances = []
    for item in filter(None, (part.strip() for part in spec.split(","))):
        name, sep, url = item.partition("=")
        name = name.strip().lower()
        if not sep or not _NAME.fullmatch(name) or not url.strip().startswith(("http://", "https://")):
            raise ValueError(f"{item!r}: expected name=https://host, with a name like 'cern' or 'in2p3'")
        token = os.environ.get(f"INDICO_TOKEN_{name.upper()}") or None
        instances.append(Instance(name=name, url=url.strip().rstrip("/"), token=token))
    return tuple(instances)
