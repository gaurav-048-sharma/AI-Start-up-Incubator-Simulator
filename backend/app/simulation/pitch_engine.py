"""
Pitch Engine — Orchestrates multi-turn interactive investor pitch simulations.
Uses the LLM service directly for flexible dialogue management.
"""

import structlog
from datetime import datetime, timezone
from typing import Optional
from app.services.llm import get_llm_service
from app.simulation.investor_agents import get_investor_profiles, get_investor_system_prompt
from app.config import get_settings

logger = structlog.get_logger()


class PitchEngine:
    """Orchestrates an interactive multi-round investor pitch simulation."""

    def __init__(self):
        self._llm_service = get_llm_service()
        self._settings = get_settings()

    async def start_interactive_pitch(
        self,
        idea: dict,
        executive_summary: str = "",
        financial_projection: str = "",
        custom_investors: list[dict] = None,
    ) -> dict:
        """
        Start an interactive pitch.
        Instead of the founder pitching first, the first investor asks an opening question based on the reports.
        """
        investors = custom_investors or get_investor_profiles(self._settings.num_investor_agents)
        first_investor = investors[0]
        
        inv_prompt = get_investor_system_prompt(first_investor)
        context = (
            f"Here is the startup idea:\nTitle: {idea.get('title')}\nDescription: {idea.get('description')}\n"
            f"Executive Summary:\n{executive_summary}\n\n"
            f"Financial Projections:\n{financial_projection}\n\n"
        )
        
        prompt = (
            f"{context}You are opening the pitch session. Based on the reports provided, ask the founder ONE tough, "
            f"critical opening question about their startup."
        )

        opening_question = await self._llm_service.generate(
            prompt=prompt,
            system_prompt=inv_prompt,
        )
        
        msg = self._msg(first_investor["name"], "investor", opening_question)
        return {"message": msg, "investors": investors}

    async def process_interactive_turn(
        self,
        idea: dict,
        transcript: list[dict],
        custom_investors: list[dict] = None,
        max_rounds: int = None,
    ) -> dict:
        """
        Process a single turn after the founder responds.
        Determines the next investor to speak, or finalizes the verdict if max rounds reached.
        Returns: {"status": "active"|"completed", "message": dict (optional), "outcome": ..., "feedback": ...}
        """
        max_rounds = max_rounds or self._settings.simulation_max_rounds
        investors = custom_investors or get_investor_profiles(self._settings.num_investor_agents)
        
        # Calculate how many founder messages are in the transcript (represents rounds completed)
        founder_messages = [m for m in transcript if m["role"] == "founder"]
        current_round = len(founder_messages)

        if current_round >= max_rounds:
            # Reached max rounds, time for verdict
            return await self._generate_final_verdicts(transcript, investors)
        
        # Pick the next investor (round robin)
        next_investor = investors[current_round % len(investors)]
        inv_prompt = get_investor_system_prompt(next_investor)
        context_str = self._build_context(transcript)
        
        prompt = (
            f"Here is the pitch conversation so far:\n{context_str}\n\n"
            f"Ask your next critical question for the founder. Be concise, direct, and stay in character."
        )

        response = await self._llm_service.generate(
            prompt=prompt,
            system_prompt=inv_prompt,
        )
        
        msg = self._msg(next_investor["name"], "investor", response)
        return {"status": "active", "message": msg}

    async def _generate_final_verdicts(self, transcript: list[dict], investors: list[dict]) -> dict:
        """Generates the final funding decision from all investors."""
        verdicts = []
        for investor in investors:
            inv_prompt = get_investor_system_prompt(investor)
            context = self._build_context(transcript, max_chars=8000)

            verdict = await self._llm_service.generate(
                prompt=(
                    f"Full pitch transcript:\n{context}\n\n"
                    "The pitch is over. Give your final verdict: INVEST, PASS, or CONDITIONAL.\n"
                    "If INVEST: state amount and valuation.\n"
                    "Provide detailed feedback on why you made this decision."
                ),
                system_prompt=inv_prompt,
            )
            verdicts.append({"investor": investor["name"], "verdict": verdict})

        result = self._parse_outcome(verdicts)
        
        # Add the verdict messages to return so they can be shown in chat
        verdict_msgs = [self._msg(v["investor"], "verdict", v["verdict"]) for v in verdicts]
        result["status"] = "completed"
        result["verdict_messages"] = verdict_msgs
        return result

    def _msg(self, speaker: str, role: str, content: str) -> dict:
        return {
            "speaker": speaker,
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _build_context(self, transcript: list[dict], max_chars: int = 4000) -> str:
        context = ""
        for msg in transcript[-10:]:  # Include more recent messages for context
            entry = f"[{msg['speaker']}]: {msg['content']}\n\n"
            if len(context) + len(entry) > max_chars:
                break
            context += entry
        return context

    def _parse_outcome(self, verdicts: list[dict]) -> dict:
        invest_count = sum(1 for v in verdicts if "INVEST" in v["verdict"].upper() and "PASS" not in v["verdict"].upper())
        total = len(verdicts)

        if invest_count >= total / 2:
            outcome = "funded"
        elif invest_count > 0:
            outcome = "conditional"
        else:
            outcome = "passed"

        feedback = {v["investor"]: v["verdict"] for v in verdicts}
        
        # Simple extraction of funding offered (mock logic, could be regex)
        funding = 500000 if outcome == "funded" else None
        valuation = 5000000 if outcome == "funded" else None

        return {
            "outcome": outcome,
            "feedback": feedback,
            "funding_offered": funding,
            "valuation": valuation,
        }
