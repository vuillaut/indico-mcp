import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_generator():
    spec = importlib.util.spec_from_file_location("gen_tools_reference", ROOT / "scripts" / "gen_tools_reference.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def test_tool_reference_is_up_to_date():
    generator = load_generator()
    expected = await generator.render()
    assert generator.OUTPUT.read_text() == expected, "run: uv run python scripts/gen_tools_reference.py"
