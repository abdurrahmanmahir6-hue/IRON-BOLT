"""
IRON BOLT - Tool System
Action Layer: Enables AI to interact with the real world.
Architecture: Tool Manager coordinates all tools. No tool is used directly.
"""

from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod
from enum import Enum
import json


class ToolResult:
    """Standardized tool result format."""

    def __init__(self, success: bool, data: Any = None, error: str = None, metadata: Dict = None):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata
        }


class BaseTool(ABC):
    """
    Base Tool Interface.
    All tools must inherit from this.
    Single Responsibility: Perform one specific action.
    """

    def __init__(self, name: str, description: str, version: str = "1.0"):
        self.name = name
        self.description = description
        self.version = version
        self.enabled = True
        self.parameters = self._define_parameters()

    @abstractmethod
    def _define_parameters(self) -> Dict[str, Any]:
        """Define required parameters for this tool."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters."""
        for param_name, param_config in self.parameters.items():
            if param_config.get("required", False) and param_name not in kwargs:
                return False
        return True

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema for LLM understanding."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": self.parameters,
            "enabled": self.enabled
        }

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False


class CalculatorTool(BaseTool):
    """Basic calculator tool for AR1."""

    def __init__(self):
        super().__init__(
            name="calculator",
            description="Perform mathematical calculations",
            version="1.0"
        )

    def _define_parameters(self) -> Dict[str, Any]:
        return {
            "expression": {
                "type": "string",
                "required": True,
                "description": "Mathematical expression to evaluate"
            }
        }

    def execute(self, **kwargs) -> ToolResult:
        try:
            expression = kwargs.get("expression", "")
            # Safe evaluation - only allow basic math
            allowed_names = {
                "abs": abs, "max": max, "min": min,
                "sum": sum, "pow": pow, "round": round
            }
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FileTool(BaseTool):
    """File operations tool for AR1."""

    def __init__(self):
        super().__init__(
            name="file",
            description="Read and write files",
            version="1.0"
        )

    def _define_parameters(self) -> Dict[str, Any]:
        return {
            "action": {
                "type": "string",
                "required": True,
                "description": "Action: read, write, list"
            },
            "path": {
                "type": "string",
                "required": True,
                "description": "File or directory path"
            },
            "content": {
                "type": "string",
                "required": False,
                "description": "Content to write (for write action)"
            }
        }

    def execute(self, **kwargs) -> ToolResult:
        import os
        action = kwargs.get("action")
        path = kwargs.get("path")

        try:
            if action == "read":
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return ToolResult(success=True, data=content)

            elif action == "write":
                content = kwargs.get("content", "")
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return ToolResult(success=True, data=f"File written: {path}")

            elif action == "list":
                items = os.listdir(path)
                return ToolResult(success=True, data=items)

            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ToolManager:
    """
    Central controller for all tools.
    Single Responsibility: Register, discover, and execute tools.
    """

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.execution_history: List[Dict] = []

    def register_tool(self, tool: BaseTool):
        """Register a new tool."""
        self.tools[tool.name] = tool
        print(f"[ToolManager] Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with their schemas."""
        return [tool.get_schema() for tool in self.tools.values()]

    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool by name with given parameters.
        This is the ONLY way tools should be executed.
        """
        tool = self.tools.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"Tool not found: {tool_name}")

        if not tool.enabled:
            return ToolResult(success=False, error=f"Tool disabled: {tool_name}")

        # Validate input
        if not tool.validate_input(**kwargs):
            return ToolResult(success=False, error="Invalid parameters")

        # Execute and log
        try:
            result = tool.execute(**kwargs)
            self.execution_history.append({
                "tool": tool_name,
                "params": kwargs,
                "result": result.to_dict()
            })
            return result
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def get_tool_descriptions_for_prompt(self) -> str:
        """Get tool descriptions formatted for LLM prompts."""
        descriptions = []
        for tool in self.tools.values():
            if tool.enabled:
                schema = tool.get_schema()
                desc = f"Tool: {schema['name']}\n"
                desc += f"Description: {schema['description']}\n"
                desc += f"Parameters: {json.dumps(schema['parameters'])}\n"
                descriptions.append(desc)
        return "\n\n".join(descriptions)


# Singleton instance
_tool_manager_instance = None

def get_tool_manager() -> ToolManager:
    """Get or create global tool manager."""
    global _tool_manager_instance
    if _tool_manager_instance is None:
        _tool_manager_instance = ToolManager()
    return _tool_manager_instance
