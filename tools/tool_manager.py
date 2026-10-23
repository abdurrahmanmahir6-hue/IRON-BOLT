"""
IRON BOLT - Tool System
Action Layer: Enables AI to interact with the real world.
Architecture: Tool Manager coordinates all tools. No tool is used directly.
"""

import ast
import math
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Union
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
            result = self._evaluate_expression(expression)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    @staticmethod
    def _evaluate_expression(expression: str) -> Union[int, float]:
        """Evaluate a deliberately small arithmetic-only expression grammar."""
        if not isinstance(expression, str) or not expression.strip():
            raise ValueError("Expression must be a non-empty string")
        if len(expression) > 256:
            raise ValueError("Expression is too long")

        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise ValueError("Invalid arithmetic expression") from exc

        def validate_number(value: Any) -> Union[int, float]:
            if type(value) not in (int, float):
                raise ValueError("Only real numeric constants are allowed")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("Non-finite numbers are not allowed")
            if isinstance(value, int) and value.bit_length() > 4096:
                raise ValueError("Integer result is too large")
            return value

        def evaluate(node: ast.AST) -> Union[int, float]:
            if isinstance(node, ast.Constant):
                return validate_number(node.value)

            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                operand = evaluate(node.operand)
                return validate_number(operand if isinstance(node.op, ast.UAdd) else -operand)

            if isinstance(node, ast.BinOp):
                left = evaluate(node.left)
                right = evaluate(node.right)
                if isinstance(node.op, ast.Add):
                    result = left + right
                elif isinstance(node.op, ast.Sub):
                    result = left - right
                elif isinstance(node.op, ast.Mult):
                    result = left * right
                elif isinstance(node.op, ast.Div):
                    result = left / right
                elif isinstance(node.op, ast.FloorDiv):
                    result = left // right
                elif isinstance(node.op, ast.Mod):
                    result = left % right
                elif isinstance(node.op, ast.Pow):
                    if abs(right) > 128:
                        raise ValueError("Exponent is too large")
                    result = left ** right
                else:
                    raise ValueError("Unsupported arithmetic operator")
                return validate_number(result)

            raise ValueError("Unsupported expression")

        return evaluate(tree.body)


class FileTool(BaseTool):
    """File operations constrained to one explicitly approved workspace root."""

    def __init__(self, workspace_root: Optional[Union[str, os.PathLike]] = None):
        self._workspace_root: Optional[Path] = None
        if workspace_root is not None:
            root = Path(workspace_root)
            if root.is_absolute() and root.is_dir():
                self._workspace_root = root.resolve()
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
        action = kwargs.get("action")
        path = kwargs.get("path")

        try:
            resolved_path = self._resolve_workspace_path(path)
            if action == "read":
                with open(resolved_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return ToolResult(success=True, data=content)

            elif action == "write":
                content = kwargs.get("content", "")
                with open(resolved_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return ToolResult(success=True, data=f"File written: {path}")

            elif action == "list":
                items = os.listdir(resolved_path)
                return ToolResult(success=True, data=items)

            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _resolve_workspace_path(self, path: Union[str, os.PathLike]) -> Path:
        """Resolve a relative path and reject every escape from the approved root."""
        if self._workspace_root is None:
            raise PermissionError("File tool is disabled: no approved workspace root is configured")
        if not isinstance(path, (str, os.PathLike)):
            raise ValueError("Path must be a relative path")

        requested_path = Path(path)
        if requested_path.is_absolute():
            raise PermissionError("Absolute paths are not allowed")

        # resolve(strict=False) follows existing symlinks, including a symlinked
        # parent of a not-yet-created file. The containment check therefore
        # rejects traversal and symlink targets outside the approved root.
        resolved_path = (self._workspace_root / requested_path).resolve(strict=False)
        try:
            resolved_path.relative_to(self._workspace_root)
        except ValueError as exc:
            raise PermissionError("Path escapes the approved workspace root") from exc
        return resolved_path


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

    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Alias for execute()."""
        return self.execute(tool_name, **kwargs)

    def dispatch(self, tool_name: str, **kwargs) -> Any:
        """Contract for ToolDispatcher interface."""
        return self.execute(tool_name, **kwargs)

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
