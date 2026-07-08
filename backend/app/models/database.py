"""
SQLite database client and helper functions using aiosqlite.
Provides typed access to all database tables with error handling.
"""

import structlog
import aiosqlite
import json
import os
import uuid
from typing import Optional, Any, List

from app.config import get_settings

logger = structlog.get_logger()

def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        val = row[idx]
        # Attempt to parse JSON fields if possible, since we stored JSON as TEXT
        if isinstance(val, str) and val.startswith('{') and val.endswith('}'):
            try:
                val = json.loads(val)
            except:
                pass
        elif isinstance(val, str) and val.startswith('[') and val.endswith(']'):
            try:
                val = json.loads(val)
            except:
                pass
        d[col[0]] = val
    return d

from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_connection():
    """Get an aiosqlite database connection."""
    settings = get_settings()
    db_path = settings.sqlite_db_path
    
    # Ensure directory exists if path contains one
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = _dict_factory
        yield conn

async def init_db():
    """Initialize the SQLite database with the schema."""
    settings = get_settings()
    db_path = settings.sqlite_db_path
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    
    if os.path.exists(schema_path):
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        
        async with get_db_connection() as conn:
            await conn.executescript(schema_sql)
            await conn.commit()
            logger.info("Database schema initialized", db_path=db_path)

def _serialize_json(data: dict) -> dict:
    """Helper to convert dicts to JSON strings for SQLite insertion."""
    res = {}
    for k, v in data.items():
        if isinstance(v, (dict, list)):
            res[k] = json.dumps(v)
        else:
            res[k] = v
    return res

class DatabaseService:
    """High-level database operations for the incubator platform."""

    def __init__(self):
        pass

    # ── Profiles / Users ──────────────────────────────────────────

    async def get_profile(self, user_id: str) -> Optional[dict]:
        try:
            async with get_db_connection() as conn:
                async with conn.execute("SELECT * FROM profiles WHERE id = ?", (user_id,)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logger.error("Failed to get profile", user_id=user_id, error=str(e))
            return None

    async def get_profile_by_email(self, email: str) -> Optional[dict]:
        try:
            async with get_db_connection() as conn:
                async with conn.execute("SELECT * FROM profiles WHERE email = ?", (email,)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logger.error("Failed to get profile by email", email=email, error=str(e))
            return None

    async def update_profile(self, user_id: str, data: dict) -> Optional[dict]:
        try:
            data = _serialize_json(data)
            if not data:
                return await self.get_profile(user_id)
                
            set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
            values = list(data.values()) + [user_id]
            
            async with get_db_connection() as conn:
                # Check if exists
                async with conn.execute("SELECT 1 FROM profiles WHERE id = ?", (user_id,)) as cursor:
                    exists = await cursor.fetchone()
                
                if exists:
                    await conn.execute(f"UPDATE profiles SET {set_clause} WHERE id = ?", values)
                else:
                    cols = ", ".join(data.keys())
                    placeholders = ", ".join(["?"] * len(data))
                    await conn.execute(f"INSERT INTO profiles (id, {cols}) VALUES (?, {placeholders})", [user_id] + list(data.values()))
                await conn.commit()
                
            return await self.get_profile(user_id)
        except Exception as e:
            logger.error("Failed to update profile", user_id=user_id, error=str(e))
            return None

    # ── Ideas ────────────────────────────────────────────────────

    async def create_idea(self, idea_data: dict) -> Optional[dict]:
        try:
            if "id" not in idea_data:
                idea_data["id"] = str(uuid.uuid4())
            data = _serialize_json(idea_data)
            cols = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            
            async with get_db_connection() as conn:
                await conn.execute(f"INSERT INTO ideas ({cols}) VALUES ({placeholders})", list(data.values()))
                await conn.commit()
                
            logger.info("Idea created", idea_id=idea_data["id"])
            return await self.get_idea(idea_data["id"])
        except Exception as e:
            logger.error("Failed to create idea", error=str(e))
            return None

    async def get_idea(self, idea_id: str) -> Optional[dict]:
        try:
            async with get_db_connection() as conn:
                async with conn.execute("SELECT * FROM ideas WHERE id = ?", (idea_id,)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logger.error("Failed to get idea", idea_id=idea_id, error=str(e))
            return None

    async def get_user_ideas(self, user_id: str, organization_id: Optional[str] = None) -> list[dict]:
        try:
            settings = get_settings()
            async with get_db_connection() as conn:
                if settings.bypass_auth:
                    query = "SELECT * FROM ideas ORDER BY created_at DESC"
                    params = ()
                elif organization_id:
                    query = "SELECT * FROM ideas WHERE organization_id = ? ORDER BY created_at DESC"
                    params = (organization_id,)
                else:
                    query = "SELECT * FROM ideas WHERE user_id = ? ORDER BY created_at DESC"
                    params = (user_id,)
                    
                async with conn.execute(query, params) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logger.error("Failed to get ideas", user_id=user_id, org_id=organization_id, error=str(e))
            return []

    async def get_ideas(self, organization_id: Optional[str] = None, user_id: Optional[str] = None) -> dict:
        try:
            settings = get_settings()
            async with get_db_connection() as conn:
                if settings.bypass_auth:
                    query = "SELECT * FROM ideas ORDER BY created_at DESC"
                    params = ()
                elif organization_id:
                    query = "SELECT * FROM ideas WHERE organization_id = ? ORDER BY created_at DESC"
                    params = (organization_id,)
                elif user_id:
                    query = "SELECT * FROM ideas WHERE user_id = ? ORDER BY created_at DESC"
                    params = (user_id,)
                else:
                    query = "SELECT * FROM ideas ORDER BY created_at DESC"
                    params = ()
                    
                async with conn.execute(query, params) as cursor:
                    ideas = await cursor.fetchall()
                    return {"ideas": ideas, "total": len(ideas)}
        except Exception as e:
            logger.error("Failed to list ideas", user_id=user_id, org_id=organization_id, error=str(e))
            return {"ideas": [], "total": 0}

    async def update_idea(self, idea_id: str, data: dict) -> Optional[dict]:
        try:
            data = _serialize_json(data)
            if not data:
                return await self.get_idea(idea_id)
                
            set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
            values = list(data.values()) + [idea_id]
            
            async with get_db_connection() as conn:
                await conn.execute(f"UPDATE ideas SET {set_clause} WHERE id = ?", values)
                await conn.commit()
                
            return await self.get_idea(idea_id)
        except Exception as e:
            logger.error("Failed to update idea", idea_id=idea_id, error=str(e))
            return None

    async def clear_idea_artifacts(self, idea_id: str) -> bool:
        try:
            async with get_db_connection() as conn:
                await conn.execute("DELETE FROM agent_activities WHERE idea_id = ?", (idea_id,))
                await conn.execute("DELETE FROM workflow_states WHERE idea_id = ?", (idea_id,))
                await conn.execute("DELETE FROM reports WHERE idea_id = ?", (idea_id,))
                await conn.execute("DELETE FROM simulations WHERE idea_id = ?", (idea_id,))
                await conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to clear idea artifacts", idea_id=idea_id, error=str(e))
            return False

    async def delete_idea(self, idea_id: str) -> bool:
        try:
            await self.clear_idea_artifacts(idea_id)
            async with get_db_connection() as conn:
                await conn.execute("DELETE FROM ideas WHERE id = ?", (idea_id,))
                await conn.commit()
            logger.info("Idea deleted", idea_id=idea_id)
            return True
        except Exception as e:
            logger.error("Failed to delete idea", idea_id=idea_id, error=str(e))
            return False

    # ── Agent Activities ─────────────────────────────────────────

    async def log_agent_activity(self, activity_data: dict) -> Optional[dict]:
        try:
            if "id" not in activity_data:
                activity_data["id"] = str(uuid.uuid4())
            data = _serialize_json(activity_data)
            cols = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            
            async with get_db_connection() as conn:
                await conn.execute(f"INSERT INTO agent_activities ({cols}) VALUES ({placeholders})", list(data.values()))
                await conn.commit()
                
            # Fetch back
            async with get_db_connection() as conn:
                async with conn.execute("SELECT * FROM agent_activities WHERE id = ?", (activity_data["id"],)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logger.error("Failed to log agent activity", error=str(e))
            return None

    async def get_idea_activities(self, idea_id: str) -> list[dict]:
        try:
            async with get_db_connection() as conn:
                async with conn.execute("SELECT * FROM agent_activities WHERE idea_id = ? ORDER BY started_at DESC", (idea_id,)) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logger.error("Failed to get agent activities", idea_id=idea_id, error=str(e))
            return []

    async def update_agent_activity(self, activity_id: str, data: dict) -> Optional[dict]:
        try:
            data = _serialize_json(data)
            if not data:
                pass
            else:
                set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
                values = list(data.values()) + [activity_id]
                
                async with get_db_connection() as conn:
                    await conn.execute(f"UPDATE agent_activities SET {set_clause} WHERE id = ?", values)
                    await conn.commit()
                    
            async with get_db_connection() as conn:
                async with conn.execute("SELECT * FROM agent_activities WHERE id = ?", (activity_id,)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logger.error("Failed to update activity", activity_id=activity_id, error=str(e))
            return None

    # ── Workflow States ──────────────────────────────────────────

    async def save_workflow_state(self, state_data: dict) -> Optional[dict]:
        try:
            idea_id = state_data.get("idea_id")
            if not idea_id:
                return None
                
            if "id" not in state_data:
                state_data["id"] = str(uuid.uuid4())
                
            data = _serialize_json(state_data)
            
            async with get_db_connection() as conn:
                # Check if exists
                async with conn.execute("SELECT 1 FROM workflow_states WHERE idea_id = ?", (idea_id,)) as cursor:
                    exists = await cursor.fetchone()
                
                if exists:
                    set_clause = ", ".join([f"{k} = ?" for k in data.keys() if k != "id"])
                    values = [v for k, v in data.items() if k != "id"] + [idea_id]
                    await conn.execute(f"UPDATE workflow_states SET {set_clause} WHERE idea_id = ?", values)
                else:
                    cols = ", ".join(data.keys())
                    placeholders = ", ".join(["?"] * len(data))
                    await conn.execute(f"INSERT INTO workflow_states ({cols}) VALUES ({placeholders})", list(data.values()))
                await conn.commit()
                
            return await self.get_workflow_state(idea_id)
        except Exception as e:
            logger.error("Failed to save workflow state", error=str(e))
            return None

    async def get_workflow_state(self, idea_id: str) -> Optional[dict]:
        try:
            async with get_db_connection() as conn:
                async with conn.execute("SELECT * FROM workflow_states WHERE idea_id = ? ORDER BY updated_at DESC LIMIT 1", (idea_id,)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logger.error("Failed to get workflow state", idea_id=idea_id, error=str(e))
            return None

    # ── Reports ──────────────────────────────────────────────────

    async def create_report(self, report_data: dict) -> Optional[dict]:
        try:
            if "id" not in report_data:
                report_data["id"] = str(uuid.uuid4())
            data = _serialize_json(report_data)
            cols = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            
            async with get_db_connection() as conn:
                await conn.execute(f"INSERT INTO reports ({cols}) VALUES ({placeholders})", list(data.values()))
                await conn.commit()
                
            logger.info("Report created", report_id=report_data["id"])
            return await self.get_report(report_data["id"])
        except Exception as e:
            logger.error("Failed to create report", error=str(e))
            return None

    async def get_idea_reports(self, idea_id: str) -> list[dict]:
        try:
            async with get_db_connection() as conn:
                async with conn.execute("SELECT * FROM reports WHERE idea_id = ? ORDER BY created_at DESC", (idea_id,)) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logger.error("Failed to get reports", idea_id=idea_id, error=str(e))
            return []

    async def get_report(self, report_id: str) -> Optional[dict]:
        try:
            async with get_db_connection() as conn:
                async with conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logger.error("Failed to get report", report_id=report_id, error=str(e))
            return None

    # ── Simulations ──────────────────────────────────────────────

    async def create_simulation(self, sim_data: dict) -> Optional[dict]:
        try:
            if "id" not in sim_data:
                sim_data["id"] = str(uuid.uuid4())
            data = _serialize_json(sim_data)
            cols = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            
            async with get_db_connection() as conn:
                await conn.execute(f"INSERT INTO simulations ({cols}) VALUES ({placeholders})", list(data.values()))
                await conn.commit()
                
            logger.info("Simulation created", sim_id=sim_data["id"])
            return await self.get_simulation(sim_data["id"])
        except Exception as e:
            logger.error("Failed to create simulation", error=str(e))
            return None

    async def get_simulation(self, sim_id: str) -> Optional[dict]:
        try:
            async with get_db_connection() as conn:
                async with conn.execute("SELECT * FROM simulations WHERE id = ?", (sim_id,)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logger.error("Failed to get simulation", sim_id=sim_id, error=str(e))
            return None

    async def update_simulation(self, sim_id: str, data: dict) -> Optional[dict]:
        try:
            data = _serialize_json(data)
            if not data:
                return await self.get_simulation(sim_id)
                
            set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
            values = list(data.values()) + [sim_id]
            
            async with get_db_connection() as conn:
                await conn.execute(f"UPDATE simulations SET {set_clause} WHERE id = ?", values)
                await conn.commit()
                
            return await self.get_simulation(sim_id)
        except Exception as e:
            logger.error("Failed to update simulation", sim_id=sim_id, error=str(e))
            return None

    async def get_idea_simulations(self, idea_id: str) -> list[dict]:
        try:
            async with get_db_connection() as conn:
                async with conn.execute("SELECT * FROM simulations WHERE idea_id = ? ORDER BY created_at DESC", (idea_id,)) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logger.error("Failed to list simulations", idea_id=idea_id, error=str(e))
            return []

    async def delete_simulation(self, sim_id: str) -> bool:
        try:
            async with get_db_connection() as conn:
                await conn.execute("DELETE FROM simulations WHERE id = ?", (sim_id,))
                await conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to delete simulation", sim_id=sim_id, error=str(e))
            return False


_db_service: Optional[DatabaseService] = None

def get_db_service() -> DatabaseService:
    """Get or create the global database service singleton."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
