"""
IRON BOLT - Workflow Engine
Process Coordination Layer: Manages multi-step tasks.
Architecture: Workflow Engine coordinates steps but doesn't make decisions.
"""

from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from datetime import datetime
import json


class WorkflowState(Enum):
    """Workflow execution states."""
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepResult:
    """Result of a workflow step execution."""

    def __init__(self, success: bool, data: Any = None, error: str = None):
        self.success = success
        self.data = data
        self.error = error
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp
        }


class WorkflowStep:
    """Single step in a workflow."""

    def __init__(self, name: str, description: str, action: str, 
                 params: Dict = None, depends_on: List[str] = None):
        self.name = name
        self.description = description
        self.action = action  # tool_name or "llm" or "memory"
        self.params = params or {}
        self.depends_on = depends_on or []
        self.result: Optional[StepResult] = None
        self.state = WorkflowState.CREATED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "action": self.action,
            "params": self.params,
            "depends_on": self.depends_on,
            "state": self.state.value,
            "result": self.result.to_dict() if self.result else None
        }


class WorkflowDefinition:
    """Defines a workflow structure."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: List[WorkflowStep] = []
        self.metadata: Dict[str, Any] = {}

    def add_step(self, step: WorkflowStep):
        """Add a step to the workflow."""
        self.steps.append(step)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "metadata": self.metadata
        }


class WorkflowContext:
    """Holds context during workflow execution."""

    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.step_results: Dict[str, StepResult] = {}
        self.started_at = datetime.now().isoformat()
        self.completed_at = None

    def set_variable(self, key: str, value: Any):
        self.variables[key] = value

    def get_variable(self, key: str, default=None):
        return self.variables.get(key, default)

    def add_step_result(self, step_name: str, result: StepResult):
        self.step_results[step_name] = result


class WorkflowEngine:
    """
    Workflow Engine - coordinates multi-step task execution.
    AR1: Sequential execution only.
    Future: Parallel, conditional, retry support.
    """

    def __init__(self, tool_manager=None, provider_manager=None, memory_manager=None):
        self.tool_manager = tool_manager
        self.provider_manager = provider_manager
        self.memory_manager = memory_manager
        self.active_workflows: Dict[str, WorkflowDefinition] = {}

    def create_workflow(self, name: str, description: str = "") -> WorkflowDefinition:
        """Create a new workflow definition."""
        return WorkflowDefinition(name, description)

    def execute(self, workflow: WorkflowDefinition, context: WorkflowContext = None) -> Dict[str, Any]:
        """
        Execute a workflow sequentially.
        AR1 Implementation: Simple sequential execution.
        """
        if context is None:
            context = WorkflowContext()

        workflow_id = f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.active_workflows[workflow_id] = workflow

        results = {
            "workflow_id": workflow_id,
            "workflow_name": workflow.name,
            "state": WorkflowState.RUNNING.value,
            "steps": [],
            "started_at": datetime.now().isoformat()
        }

        try:
            for step in workflow.steps:
                step.state = WorkflowState.RUNNING
                print(f"[Workflow] Executing step: {step.name}")

                # Execute step based on action type
                if step.action == "llm":
                    result = self._execute_llm_step(step, context)
                elif step.action == "memory":
                    result = self._execute_memory_step(step, context)
                elif step.action.startswith("tool:"):
                    tool_name = step.action.split(":", 1)[1]
                    result = self._execute_tool_step(step, tool_name, context)
                else:
                    result = StepResult(False, error=f"Unknown action: {step.action}")

                step.result = result
                context.add_step_result(step.name, result)

                step_data = step.to_dict()
                results["steps"].append(step_data)

                if not result.success:
                    step.state = WorkflowState.FAILED
                    results["state"] = WorkflowState.FAILED.value
                    results["error"] = result.error
                    return results

                step.state = WorkflowState.COMPLETED

            results["state"] = WorkflowState.COMPLETED.value
            context.completed_at = datetime.now().isoformat()

        except Exception as e:
            results["state"] = WorkflowState.FAILED.value
            results["error"] = str(e)

        results["completed_at"] = datetime.now().isoformat()
        return results

    def _execute_llm_step(self, step: WorkflowStep, context: WorkflowContext) -> StepResult:
        """Execute an LLM step."""
        try:
            if not self.provider_manager:
                return StepResult(False, error="No provider manager available")

            prompt = step.params.get("prompt", "")
            # Get active provider and generate response
            provider = self.provider_manager.get_active_provider()
            response = provider.generate(prompt)

            return StepResult(True, data=response)
        except Exception as e:
            return StepResult(False, error=str(e))

    def _execute_tool_step(self, step: WorkflowStep, tool_name: str, context: WorkflowContext) -> StepResult:
        """Execute a tool step."""
        try:
            if not self.tool_manager:
                return StepResult(False, error="No tool manager available")

            result = self.tool_manager.execute(tool_name, **step.params)
            return StepResult(result.success, data=result.data, error=result.error)
        except Exception as e:
            return StepResult(False, error=str(e))

    def _execute_memory_step(self, step: WorkflowStep, context: WorkflowContext) -> StepResult:
        """Execute a memory step."""
        try:
            if not self.memory_manager:
                return StepResult(False, error="No memory manager available")

            action = step.params.get("memory_action", "search")
            query = step.params.get("query", "")

            if action == "search":
                results = self.memory_manager.search(query)
                return StepResult(True, data=results)
            elif action == "save":
                content = step.params.get("content", "")
                self.memory_manager.save(content)
                return StepResult(True, data="Memory saved")
            else:
                return StepResult(False, error=f"Unknown memory action: {action}")

        except Exception as e:
            return StepResult(False, error=str(e))


# Singleton instance
_workflow_engine_instance = None

def get_workflow_engine(tool_manager=None, provider_manager=None, memory_manager=None) -> WorkflowEngine:
    """Get or create global workflow engine."""
    global _workflow_engine_instance
    if _workflow_engine_instance is None:
        _workflow_engine_instance = WorkflowEngine(tool_manager, provider_manager, memory_manager)
    return _workflow_engine_instance
