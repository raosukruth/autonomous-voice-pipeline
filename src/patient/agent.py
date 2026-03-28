# LLM-powered patient agent.
from openai import AsyncOpenAI
from src.patient.scenarios import PatientScenario


GOODBYE_PHRASES = {
    "goodbye", "good bye", "bye", "have a good day", "have a great day",
    "take care", "thanks for calling", "thank you for calling",
    "is there anything else", "we'll see you then", "see you then",
}


class PatientAgent:
    # LLM-powered patient that generates conversational responses.

    def __init__(self, api_key: str, scenario: PatientScenario,
                 model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.scenario = scenario
        self.model = model
        self.conversation_history: list = []
        self.system_message = {"role": "system", "content": scenario.system_prompt}
        self.dynamic_context: str = ""

    async def get_opening_line(self) -> str:
        # Return opening line and record it in history.
        text = self.scenario.opening_line
        self.conversation_history.append({"role": "assistant", "content": text})
        return text

    async def generate_response(self, agent_utterance: str) -> str:
        # Generate patient response to what the PGAI agent just said.
        self.conversation_history.append({"role": "user", "content": agent_utterance})
        await self._refresh_dynamic_context()
        messages = [self.system_message]
        if self.dynamic_context:
            messages.append({
                "role": "system",
                "content": f"Situation update: {self.dynamic_context}",
            })
        messages += self.conversation_history
        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=150,
            temperature=0.8,
        )
        response_text = completion.choices[0].message.content.strip()
        self.conversation_history.append({"role": "assistant", "content": response_text})
        return response_text

    async def _refresh_dynamic_context(self) -> None:
        # Every 3 agent turns, summarize progress and update the injected context.
        turn_count = sum(1 for m in self.conversation_history if m["role"] == "user")
        if turn_count == 0 or turn_count % 3 != 0:
            return
        recent = self.conversation_history[-6:]
        history_text = "\n".join(
            f"{'Agent' if m['role'] == 'user' else 'You'}: {m['content']}"
            for m in recent
        )
        summary_prompt = (
            f"You are {self.scenario.name}. Your original goal: {self.scenario.opening_line}\n"
            f"Recent conversation:\n{history_text}\n\n"
            "In one sentence, from YOUR perspective as the patient: what has been "
            "accomplished and what do you still need? "
            "Example: 'I gave my name and DOB, I still need them to confirm the appointment time.'"
        )
        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=60,
            temperature=0.3,
        )
        self.dynamic_context = completion.choices[0].message.content.strip()

    async def should_hang_up(self, agent_utterance: str) -> bool:
        # Return True if the conversation has naturally concluded.
        agent_lower = agent_utterance.lower()
        agent_goodbye = any(phrase in agent_lower for phrase in GOODBYE_PHRASES)
        if not agent_goodbye:
            return False
        if not self.conversation_history:
            return False
        last_patient = next(
            (m["content"].lower() for m in reversed(self.conversation_history)
             if m["role"] == "assistant"),
            "",
        )
        patient_goodbye = any(phrase in last_patient for phrase in GOODBYE_PHRASES)
        return patient_goodbye

    def get_conversation_history(self) -> list:
        # Return full conversation history.
        return list(self.conversation_history)

    def reset(self) -> None:
        # Clear conversation history for reuse with same scenario.
        self.conversation_history = []
        self.dynamic_context = ""
