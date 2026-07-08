"""
Build Engine - AI software factory.
Manages AI developers that take an idea and generate a codebase.
"""

import json
import structlog
from typing import Optional
from textwrap import dedent

from app.services.llm import get_llm_service
from app.models.database import get_db_service

logger = structlog.get_logger()

class BuildEngine:
    def __init__(self, db_service=None):
        self.db = db_service or get_db_service()
        self.llm_service = get_llm_service()

    async def initialize_build(self, idea: dict, reports: list[dict]) -> dict:
        logger.info("Initializing build phase", idea_id=idea["id"])
        
        context = ""
        for r in reports:
            context += f"\n--- {r.get('report_type')} ---\n"
            content = r.get("content", {})
            if isinstance(content, dict):
                context += json.dumps(content)
            else:
                context += str(content)
                
        prompt = f"""
        We are building a software MVP for the following startup idea:
        TITLE: {idea.get('title')}
        DESCRIPTION: {idea.get('description')}
        INDUSTRY: {idea.get('industry')}
        
        BUSINESS CONTEXT:
        {context}
        
        TASK:
        Generate a working, single-page HTML/CSS/JS MVP for this startup.
        It should look professional and demonstrate the core value proposition.
        
        OUTPUT FORMAT:
        You MUST return ONLY valid JSON in the following format, with no markdown code blocks or other text:
        {{
            "index.html": "<!DOCTYPE html><html>...</html>",
            "styles.css": "body {{ ... }}",
            "app.js": "console.log('init');"
        }}
        """

        try:
            result = await self.llm_service.generate(prompt)
            output_str = str(result).strip()
            if output_str.startswith("```json"):
                output_str = output_str[7:]
            if output_str.startswith("```"):
                output_str = output_str[3:]
            if output_str.endswith("```"):
                output_str = output_str[:-3]
                
            codebase = json.loads(output_str)
            return codebase
        except Exception as e:
            logger.error("Failed to generate initial codebase", error=str(e))
            return {
                "index.html": f"<h1>{idea.get('title', 'MVP')}</h1><p>Welcome to the MVP.</p>",
                "styles.css": "body { font-family: sans-serif; padding: 2rem; }",
                "app.js": "// App initialized"
            }

    async def process_feedback(self, idea: dict, current_codebase: dict, user_message: str) -> dict:
        prompt = f"""
        We are iterating on a software MVP for: {idea.get('title')}.
        
        CURRENT CODEBASE (JSON):
        {json.dumps(current_codebase)}
        
        USER FEEDBACK:
        "{user_message}"
        
        TASK:
        Update the codebase to implement the user's feedback. 
        Modify the existing files or create new ones if necessary.
        
        OUTPUT FORMAT:
        You MUST return ONLY valid JSON in the following format, with no markdown code blocks or other text:
        {{
            "index.html": "<!DOCTYPE html><html>...</html>",
            "styles.css": "body {{ ... }}",
            "app.js": "console.log('init');"
        }}
        """

        try:
            result = await self.llm_service.generate(prompt)
            output_str = str(result).strip()
            if output_str.startswith("```json"):
                output_str = output_str[7:]
            if output_str.startswith("```"):
                output_str = output_str[3:]
            if output_str.endswith("```"):
                output_str = output_str[:-3]
                
            new_codebase = json.loads(output_str)
            return new_codebase
        except Exception as e:
            logger.error("Failed to update codebase", error=str(e))
            return current_codebase
