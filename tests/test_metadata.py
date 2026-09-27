import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_versions_agree():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    codemeta = json.loads((ROOT / "codemeta.json").read_text())
    citation = next(
        line.split(":", 1)[1].strip().strip('"')
        for line in (ROOT / "CITATION.cff").read_text().splitlines()
        if line.startswith("version:")
    )
    assert codemeta["version"] == codemeta["softwareVersion"] == citation == version
    assert f"## [{version}]" in (ROOT / "CHANGELOG.md").read_text()
