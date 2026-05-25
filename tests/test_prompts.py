"""Tests for runtime prompt files."""

from pathlib import Path


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"

REQUIRED_PROMPTS = {
    "planner.txt": "Output strictly valid JSON matching the QueryPlan schema. No preamble. No markdown fences.",
    "sql_generator.txt": "Output strictly valid JSON matching the ValidatedQuery schema. No preamble. No markdown fences.",
    "critic.txt": "Output strictly valid JSON matching the CritiqueResult schema. No preamble. No markdown fences.",
    "arbiter.txt": "Output strictly valid JSON matching the ArbitrationResult schema. No preamble. No markdown fences.",
    "synthesizer.txt": "Output strictly valid JSON matching the InsightReport schema. No preamble. No markdown fences.",
}


def test_required_prompt_files_exist() -> None:
    for filename in REQUIRED_PROMPTS:
        assert (PROMPT_DIR / filename).is_file()


def test_prompt_files_are_not_empty() -> None:
    for filename in REQUIRED_PROMPTS:
        text = (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()

        assert text


def test_prompt_files_end_with_required_instruction() -> None:
    for filename, required_ending in REQUIRED_PROMPTS.items():
        text = (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()

        assert text.endswith(required_ending)
