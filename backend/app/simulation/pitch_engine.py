"""
Pitch Engine — Orchestrates multi-turn investor pitch simulations.
Uses the LLM service directly for flexible dialogue management.
"""

import structlog
from datetime import datetime, timezone
from app.services.llm import get_llm_service
from app.simulation.founder_agent import build_founder_system_prompt
from app.simulation.investor_agents import get_investor_profiles, get_investor_system_prompt
from app.config import get_settings

logger = structlog.get_logger()


class PitchEngine:
    """Orchestrates a multi-round investor pitch simulation."""

    def __init__(self):
        self._llm_service = get_llm_service()
        self._settings = get_settings()

    async def run_pitch(
        self,
        idea: dict,
        executive_summary: str = "",
        financial_projection: str = "",
        custom_investors: list[dict] = None,
        max_rounds: int = None,
    ) -> dict:
        """
        Run a complete pitch simulation.

        Returns dict with: transcript, outcome, feedback, funding_offered, valuation
        """
        max_rounds = max_rounds or self._settings.simulation_max_rounds
        investors = custom_investors or get_investor_profiles(self._settings.num_investor_agents)
        founder_prompt = build_founder_system_prompt(idea, executive_summary, financial_projection)

        transcript = []
        logger.info("Pitch simulation starting", num_investors=len(investors), max_rounds=max_rounds)

        # Round 1: Founder's opening pitch
        opening = await self._llm_service.generate(
            prompt="Deliver your opening pitch (2-3 minutes). Cover the problem, solution, market, traction, and ask.",
            system_prompt=founder_prompt,
        )
        transcript.append(self._msg("Founder", "founder", opening))

        # Rounds 2+: Q&A with each investor
        for round_num in range(1, max_rounds):
            for investor in investors:
                inv_prompt = get_investor_system_prompt(investor)
                context = self._build_context(transcript)

                # Investor asks questions
                inv_question = await self._llm_service.generate(
                    prompt=f"Based on the pitch so far:\n{context}\n\nAsk your questions for round {round_num}.",
                    system_prompt=inv_prompt,
                )
                transcript.append(self._msg(investor["name"], "investor", inv_question))

                # Founder responds
                founder_response = await self._llm_service.generate(
                    prompt=f"Respond to {investor['name']}'s questions:\n{inv_question}",
                    system_prompt=founder_prompt,
                )
                transcript.append(self._msg("Founder", "founder", founder_response))

        # Final verdicts from each investor
        verdicts = []
        for investor in investors:
            inv_prompt = get_investor_system_prompt(investor)
            context = self._build_context(transcript)

            verdict = await self._llm_service.generate(
                prompt=(
                    f"Full pitch transcript:\n{context}\n\n"
                    "Give your final verdict: INVEST, PASS, or CONDITIONAL.\n"
                    "If INVEST: state amount and valuation.\n"
                    "Provide detailed feedback."
                ),
                system_prompt=inv_prompt,
            )
            transcript.append(self._msg(investor["name"], "verdict", verdict))
            verdicts.append({"investor": investor["name"], "verdict": verdict})

        # Parse outcome
        result = self._parse_outcome(verdicts)
        result["transcript"] = transcript

        logger.info("Pitch simulation completed", outcome=result.get("outcome"))
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
        for msg in transcript[-6:]:  # Last 6 messages for context
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

        return {
            "outcome": outcome,
            "feedback": feedback,
            "funding_offered": None,  # Could be parsed from verdicts
            "valuation": None,
        }
