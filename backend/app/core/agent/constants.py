from pathlib import Path


APP_ROOT = Path(__file__).parent.parent.parent.resolve()

PROMPT_ROOT_ECHOMIND = APP_ROOT / "prompts" / "echomind"
PROMPT_ROOT_AUTODOC = APP_ROOT / "prompts" / "autodoc"
