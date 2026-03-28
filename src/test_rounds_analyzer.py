import pytest

from src.rounds_analyzer import (
    build_round_stats,
    generate_round_ranking_report,
    list_round_dirs,
)


def write_transcript(path, lines):
    path.write_text("\n".join(lines), encoding="utf-8")


def test_list_round_dirs_sorts_numerically(tmp_path):
    (tmp_path / "round-10").mkdir()
    (tmp_path / "round-2").mkdir()
    (tmp_path / "round-1").mkdir()
    (tmp_path / "misc").mkdir()

    rounds = list_round_dirs(str(tmp_path))

    assert [path.name for path in rounds] == ["round-1", "round-2", "round-10"]


def test_build_round_stats_counts_good_bad_and_not_meaningful(tmp_path):
    round_dir = tmp_path / "round-1"
    transcript_dir = round_dir / "output" / "transcripts"
    transcript_dir.mkdir(parents=True)
    (round_dir / "output" / "bug_report.md").write_text("Issue summary", encoding="utf-8")

    write_transcript(
        transcript_dir / "good.txt",
        [
            "[1.0] AGENT: Hello",
            "[2.0] PATIENT: I need an appointment",
            "[3.0] AGENT: Sure",
            "[4.0] PATIENT: Tuesday works",
            "[5.0] AGENT: Great",
            "[6.0] PATIENT: Thank you",
            "[7.0] AGENT: Your appointment is set",
            "[8.0] PATIENT: Goodbye",
        ],
    )
    write_transcript(
        transcript_dir / "bad.txt",
        [
            "[1.0] AGENT: Hello",
            "[2.0] PATIENT: Is this Dr. Smith?",
            "[3.0] AGENT: I don't have that information",
            "[4.0] PATIENT: Can you check?",
            "[5.0] AGENT: How may I help you today",
            "[6.0] PATIENT: I already said",
            "[7.0] AGENT: Try searching online",
            "[8.0] PATIENT: Okay",
        ],
    )
    write_transcript(
        transcript_dir / "short.txt",
        [
            "[1.0] AGENT: Hello",
            "[2.0] PATIENT: Hi",
            "[3.0] AGENT: Bye",
        ],
    )

    stats = build_round_stats(round_dir)

    assert stats.total_conversations == 3
    assert stats.meaningful_conversations == 2
    assert stats.good_conversations == 1
    assert stats.bad_conversations == 1
    assert stats.not_meaningful_conversations == 1
    assert stats.bug_report_excerpt == "Issue summary"


async def test_generate_round_ranking_report_writes_file(tmp_path, mocker):
    round_dir = tmp_path / "round-1"
    transcript_dir = round_dir / "output" / "transcripts"
    transcript_dir.mkdir(parents=True)
    (round_dir / "output" / "bug_report.md").write_text("Issue summary", encoding="utf-8")
    write_transcript(
        transcript_dir / "good.txt",
        [
            "[1.0] AGENT: Hello",
            "[2.0] PATIENT: I need an appointment",
            "[3.0] AGENT: Sure",
            "[4.0] PATIENT: Tuesday works",
            "[5.0] AGENT: Great",
            "[6.0] PATIENT: Thank you",
            "[7.0] AGENT: Your appointment is set",
            "[8.0] PATIENT: Goodbye",
        ],
    )

    mock_completion = mocker.MagicMock()
    mock_completion.choices = [mocker.MagicMock()]
    mock_completion.choices[0].message.content = "# Round Ranking\n\nround-1 is best"

    captured = {}
    mock_client = mocker.AsyncMock()

    async def create_completion(**kwargs):
        captured["prompt"] = kwargs["messages"][0]["content"]
        return mock_completion

    mock_client.chat.completions.create = create_completion
    mocker.patch("src.rounds_analyzer.AsyncOpenAI", return_value=mock_client)

    output_path = tmp_path / "rounds_report.md"
    report = await generate_round_ranking_report(
        str(tmp_path), str(output_path), "test-openai-key"
    )

    assert report == "# Round Ranking\n\nround-1 is best"
    assert output_path.read_text(encoding="utf-8") == report
    assert "round-1" in captured["prompt"]
    assert "your_side / agent_side / mixed / inconclusive" in captured["prompt"]