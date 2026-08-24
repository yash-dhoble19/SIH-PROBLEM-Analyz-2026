"""
Base Agent class and execution context tracking.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from platform_core.ai.providers import AIProvider, get_ai_provider
from platform_core.database.models import AgentRun


class BaseAgent(ABC):
    """Abstract base class for all specialized platform intelligence agents."""

    def __init__(self, name: str, ai_provider: Optional[AIProvider] = None):
        self.name = name
        self.ai = ai_provider or get_ai_provider()
        self.ai_provider = self.ai

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's core task given the shared pipeline context."""
        pass

    def execute_with_tracking(self, context: Dict[str, Any], db: Session, analysis_id: Any) -> Dict[str, Any]:
        """Executes agent with real-time database observability and duration tracking."""
        agent_run = AgentRun(
            analysis_id=analysis_id,
            agent_name=self.name,
            status="RUNNING",
            started_at=None,
            input_summary=str(context.get("summary_input", ""))[:300]
        )
        db.add(agent_run)
        db.commit()

        start_time = time.time()
        try:
            result = self.run(context)
            duration_ms = int((time.time() - start_time) * 1000)
            agent_run.status = "COMPLETED"
            agent_run.duration_ms = duration_ms
            agent_run.output_summary = str(result.get("summary_output", "Task completed"))[:300]
            db.commit()
            return result
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            agent_run.status = "FAILED"
            agent_run.duration_ms = duration_ms
            agent_run.error_message = str(e)
            db.commit()
            raise
