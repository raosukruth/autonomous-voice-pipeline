import argparse
import asyncio
import os
import re
from dataclasses import dataclass
from pathlib import Path

from openai import AsyncOpenAI
from src.config import Config

GOOD_TERMS = (
    "scheduled",
    "appointment is set",
    "you are all set",
    "booked",
    "rescheduled",
    "cancelled",
    "canceled",
    "refill",
    "goodbye",
    "have a great day",
    "anything else i can help",
    "thanks for calling",
    "thank you for calling",
    "confirmed",
    "see you",
)

BAD_TERMS = (
    "i don't have",
    "not listed",
    "try searching online",
    "could you repeat",
    "how may i help you today",
    "for demo purposes",
    "create a demo patient profile",
)

ENTRY_PATTERN = re.compile(r"^\[(?P<ts>[0-9.]+)\]\s+(?P<speaker>AGENT|PATIENT):\s*(?P<text>.*)$")


@dataclass
class TranscriptQuality:
    meaningful: bool
    good: bool


@dataclass
class RoundStats:
    name: str
    total_conversations: int
    meaningful_conversations: int
    good_conversations: int
    bad_conversations: int
    not_meaningful_conversations: int
    bug_report_excerpt: str


def list_round_dirs(base_dir: str) -> list[Path]:
    base = Path(base_dir)
    if not base.exists():
        return []
    dirs = [path for path in base.iterdir() if path.is_dir() and path.name.startswith("round-")]
    return sorted(dirs, key=round_sort_key)


def round_sort_key(path: Path) -> int:
    match = re.search(r"round-(\d+)$", path.name)
    return int(match.group(1)) if match else 0


def parse_entries(text: str) -> list[tuple[str, str]]:
    entries = []
    for line in text.splitlines():
        match = ENTRY_PATTERN.match(line.strip())
        if match:
            entries.append((match.group("speaker"), match.group("text").strip().lower()))
    return entries


def is_meaningful(entries: list[tuple[str, str]]) -> bool:
    turns = len(entries)
    agent_turns = sum(1 for speaker, _ in entries if speaker == "AGENT")
    patient_turns = sum(1 for speaker, _ in entries if speaker == "PATIENT")
    return turns >= 8 and agent_turns >= 3 and patient_turns >= 3


def contains_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def classify_transcript(path: Path) -> TranscriptQuality:
    entries = parse_entries(path.read_text(encoding="utf-8", errors="ignore"))
    if not is_meaningful(entries):
        return TranscriptQuality(meaningful=False, good=False)
    tail = " ".join(text for _, text in entries[-8:])
    good = contains_term(tail, GOOD_TERMS) and not contains_term(tail, BAD_TERMS)
    return TranscriptQuality(meaningful=True, good=good)


def read_bug_report_excerpt(round_dir: Path, max_chars: int = 4000) -> str:
    bug_report = round_dir / "output" / "bug_report.md"
    if not bug_report.exists():
        return "(no bug report found)"
    text = bug_report.read_text(encoding="utf-8", errors="ignore").strip()
    return text[:max_chars]


def build_round_stats(round_dir: Path) -> RoundStats:
    transcript_dir = round_dir / "output" / "transcripts"
    total = meaningful = good = bad = not_meaningful = 0
    if transcript_dir.exists():
        for transcript in sorted(transcript_dir.glob("*.txt")):
            total += 1
            quality = classify_transcript(transcript)
            if not quality.meaningful:
                not_meaningful += 1
            elif quality.good:
                meaningful += 1
                good += 1
            else:
                meaningful += 1
                bad += 1
    return RoundStats(
        name=round_dir.name,
        total_conversations=total,
        meaningful_conversations=meaningful,
        good_conversations=good,
        bad_conversations=bad,
        not_meaningful_conversations=not_meaningful,
        bug_report_excerpt=read_bug_report_excerpt(round_dir),
    )


def build_round_block(stats: RoundStats) -> str:
    return (
        f"## {stats.name}\n"
        f"- Total conversations: {stats.total_conversations}\n"
        f"- Meaningful conversations: {stats.meaningful_conversations}\n"
        f"- Good conversations: {stats.good_conversations}\n"
        f"- Bad conversations: {stats.bad_conversations}\n"
        f"- Not meaningful: {stats.not_meaningful_conversations}\n"
        f"- Bug report excerpt:\n{stats.bug_report_excerpt}\n"
    )


def build_round_ranking_prompt(rounds: list[RoundStats]) -> str:
    blocks = "\n".join(build_round_block(stats) for stats in rounds)
    return f"""You are evaluating multiple benchmark rounds for a phone-agent testing system.

Definitions:
- Your side: the patient simulator, orchestration, Twilio/ngrok/audio stack, and transcript generation.
- Agent side: the Pretty Good AI phone agent under test.

Use the round summaries below to rank the rounds from best to worst.
Consider:
- Share of meaningful conversations
- Ratio of good vs bad conversations
- Severity and type of issues in the bug report excerpt
- Whether the main problems appear to be on your side, the agent side, mixed, or inconclusive

Return Markdown with these sections:
1. Round Ranking
2. Per-Round Assessment
3. Fault Attribution Summary
4. Recommended Next Fixes

For each round in Per-Round Assessment include:
- rank
- round name
- quality score from 0-100
- concise judgment on conversation quality
- fault attribution: your_side / agent_side / mixed / inconclusive
- short explanation of why

ROUND DATA:
{blocks}
"""


async def generate_round_ranking_report(base_dir: str, output_path: str, api_key: str) -> str:
    rounds = [build_round_stats(path) for path in list_round_dirs(base_dir)]
    if not rounds:
        raise FileNotFoundError(f"No round folders found in {base_dir}")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required for round ranking analysis")
    client = AsyncOpenAI(api_key=api_key)
    prompt = build_round_ranking_prompt(rounds)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2500,
    )
    report = response.choices[0].message.content.strip()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(report, encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank round folders with LLM analysis")
    parser.add_argument("--base-dir", default="rounds")
    parser.add_argument("--output", default="rounds/round_ranking.md")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    # Match main app behavior: load .env and read OPENAI_API_KEY from config.
    config = Config.from_env()
    api_key = config.openai_api_key or os.getenv("OPENAI_API_KEY", "")
    report = await generate_round_ranking_report(args.base_dir, args.output, api_key)
    print(f"Saved round ranking report to {args.output}")
    print(report)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()