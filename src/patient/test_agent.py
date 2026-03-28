# Tests for PatientAgent.
import pytest
from src.patient.agent import PatientAgent
from src.patient.scenarios import PatientScenario


@pytest.fixture
def scenario():
    return PatientScenario(
        id="test",
        name="Test Patient",
        description="Test scenario",
        system_prompt="You are a patient calling to schedule an appointment.",
        opening_line="Hi, I'd like to schedule an appointment please.",
        tags=["scheduling"],
    )


# ── Step 4.2a tests ────────────────────────────────────────────────────────────

def test_patient_agent_init(scenario, mock_openai):
    agent = PatientAgent(api_key="test_key", scenario=scenario)
    assert agent.scenario is scenario
    assert agent.model == "gpt-4o-mini"
    assert agent.conversation_history == []


async def test_patient_agent_opening_line(scenario, mock_openai):
    agent = PatientAgent(api_key="test_key", scenario=scenario)
    line = await agent.get_opening_line()
    assert line == scenario.opening_line
    assert len(agent.conversation_history) == 1
    assert agent.conversation_history[0]["role"] == "assistant"
    assert agent.conversation_history[0]["content"] == scenario.opening_line


async def test_patient_agent_reset_clears_history(scenario, mock_openai):
    agent = PatientAgent(api_key="test_key", scenario=scenario)
    await agent.get_opening_line()
    assert len(agent.conversation_history) == 1
    agent.reset()
    assert agent.conversation_history == []


# ── Step 4.2b tests ────────────────────────────────────────────────────────────

async def test_generate_response_calls_openai(scenario, mock_openai):
    agent = PatientAgent(api_key="test_key", scenario=scenario)
    await agent.generate_response("What time works for you?")
    mock_openai.chat.completions.create.assert_called_once()


async def test_generate_response_includes_history(scenario, mock_openai):
    agent = PatientAgent(api_key="test_key", scenario=scenario)
    await agent.get_opening_line()
    await agent.generate_response("Can I get your name?")
    call_kwargs = mock_openai.chat.completions.create.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert len(messages) > 2


async def test_generate_response_adds_to_history(scenario, mock_openai):
    agent = PatientAgent(api_key="test_key", scenario=scenario)
    history_before = len(agent.conversation_history)
    await agent.generate_response("How can I help you?")
    assert len(agent.conversation_history) == history_before + 2  # user + assistant


async def test_generate_response_returns_string(scenario, mock_openai):
    agent = PatientAgent(api_key="test_key", scenario=scenario)
    result = await agent.generate_response("Hello, how can I help?")
    assert isinstance(result, str)
    assert len(result) > 0


async def test_should_hang_up_detects_goodbye(scenario, mock_openai):
    agent = PatientAgent(api_key="test_key", scenario=scenario)
    # Add a patient farewell to history
    agent.conversation_history.append({"role": "assistant", "content": "Thank you, goodbye!"})
    result = await agent.should_hang_up("Have a great day, goodbye!")
    assert result is True


async def test_should_hang_up_returns_false_for_normal_speech(scenario, mock_openai):
    agent = PatientAgent(api_key="test_key", scenario=scenario)
    agent.conversation_history.append({"role": "assistant", "content": "I need Tuesday afternoon."})
    result = await agent.should_hang_up("Let me check availability.")
    assert result is False
