"""
IRON BOLT - Agent System
The decision-making and coordination layer of IRON BOLT.
Follows the architecture: Agent coordinates Provider, Memory, and Tool systems.
No circular dependencies - Agent uses managers, never imports internal implementations.
"""

from typing import Dict, Any, Optional, List
from enum import Enum
import json

class AgentState(Enum):
    """Agent execution states following IRON BOLT architecture."""
    IDLE = "idle"
    RECEIVING_REQUEST = "receiving_request"
    THINKING = "thinking"
    RETRIEVING_MEMORY = "retrieving_memory"
    EXECUTING_TOOL = "executing_tool"
    WAITING_FOR_PROVIDER = "waiting_for_provider"
    BUILDING_RESPONSE = "building_response"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseAgent:
    """
    Base Agent Interface.
    All agents must inherit from this class.
    Single Responsibility: Coordinate request processing.
    """

    def __init__(self, name: str, provider_manager=None, memory_manager=None, tool_manager=None):
        self.name = name
        self.state = AgentState.IDLE
        self.provider_manager = provider_manager
        self.memory_manager = memory_manager
        self.tool_manager = tool_manager
        self.context = {}

    def process_request(self, user_request: str, **kwargs) -> Dict[str, Any]:
        """
        Main entry point for processing user requests.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement process_request")

    def set_state(self, state: AgentState):
        """Update agent state."""
        self.state = state
        print(f"[Agent:{self.name}] State changed to: {state.value}")

    def get_state(self) -> AgentState:
        """Get current agent state."""
        return self.state

    def reset(self):
        """Reset agent to initial state."""
        self.state = AgentState.IDLE
        self.context = {}


class GeneralAgent(BaseAgent):
    """
    General Purpose Agent - IRON BOLT's primary assistant agent.
    AR1 Implementation: Basic request processing with provider integration.
    Future: Will integrate Memory, Tool, and Planning systems.
    """

    def __init__(self, provider_manager=None, memory_manager=None, tool_manager=None):
        super().__init__(
            name="general_agent",
            provider_manager=provider_manager,
            memory_manager=memory_manager,
            tool_manager=tool_manager
        )
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the general agent."""
        return """You are IRON BOLT, a modular AI assistant framework.
Your job is to help users with their requests using the available tools and knowledge.
Follow these rules:
1. Be helpful, accurate, and concise
2. If you need to use tools, clearly indicate which tool and why
3. Always maintain context from the conversation
4. If unsure, ask clarifying questions

Current Mode: General Assistant
Available Capabilities: Conversation, Analysis, Code Help
"""

    def process_request(self, user_request: str, conversation_history: List[Dict] = None, **kwargs) -> Dict[str, Any]:
        """
        Process a user request through the IRON BOLT pipeline.

        Flow:
        1. Receive Request
        2. Analyze Intent (basic for AR1)
        3. Retrieve Memory (if available)
        4. Build Prompt
        5. Call Provider
        6. Process Response
        7. Update Memory (if available)
        8. Return Final Response
        """
        try:
            self.set_state(AgentState.RECEIVING_REQUEST)

            # Step 1: Basic request analysis
            self.set_state(AgentState.THINKING)
            intent = self._analyze_intent(user_request)

            # Step 2: Retrieve memory context (if memory manager available)
            memory_context = ""
            if self.memory_manager:
                self.set_state(AgentState.RETRIEVING_MEMORY)
                memory_context = self._get_memory_context(user_request)

            # Step 3: Check if tools needed (if tool manager available)
            tool_results = []
            if self.tool_manager and intent.get("needs_tool", False):
                self.set_state(AgentState.EXECUTING_TOOL)
                tool_results = self._execute_tools(intent)

            # Step 4: Build complete prompt
            prompt = self._build_prompt(
                user_request=user_request,
                memory_context=memory_context,
                tool_results=tool_results,
                conversation_history=conversation_history or []
            )

            # Step 5: Call Provider
            self.set_state(AgentState.WAITING_FOR_PROVIDER)
            if not self.provider_manager:
                raise RuntimeError("Provider Manager not configured. Cannot process request.")

            response = self._call_provider(prompt)

            # Step 6: Build final response
            self.set_state(AgentState.BUILDING_RESPONSE)
            result = {
                "success": True,
                "response": response,
                "agent": self.name,
                "state": AgentState.COMPLETED.value,
                "intent": intent,
                "tools_used": [t["tool"] for t in tool_results] if tool_results else []
            }

            # Step 7: Update memory (if available)
            if self.memory_manager:
                self._update_memory(user_request, response)

            self.set_state(AgentState.COMPLETED)
            return result

        except Exception as e:
            self.set_state(AgentState.FAILED)
            return {
                "success": False,
                "error": str(e),
                "agent": self.name,
                "state": AgentState.FAILED.value
            }

    def _analyze_intent(self, user_request: str) -> Dict[str, Any]:
        """
        Basic intent analysis for AR1.
        Future: Will use dedicated Planning & Reasoning layer.
        """
        intent = {
            "original_request": user_request,
            "needs_tool": False,
            "needs_memory": False,
            "category": "general"
        }

        # Simple keyword-based detection for AR1
        tool_keywords = ["run", "execute", "calculate", "search", "file", "read", "write"]
        memory_keywords = ["remember", "recall", "previous", "before", "last time"]

        request_lower = user_request.lower()

        for keyword in tool_keywords:
            if keyword in request_lower:
                intent["needs_tool"] = True
                intent["category"] = "tool_required"
                break

        for keyword in memory_keywords:
            if keyword in request_lower:
                intent["needs_memory"] = True
                intent["category"] = "memory_required"
                break

        return intent

    def _get_memory_context(self, user_request: str) -> str:
        """Retrieve relevant memory context."""
        try:
            if self.memory_manager:
                memories = self.memory_manager.search(user_request)
                if memories:
                    return "\n".join([f"- {m}" for m in memories])
        except Exception as e:
            print(f"[Memory Warning] Could not retrieve memory: {e}")
        return ""

    def _execute_tools(self, intent: Dict) -> List[Dict]:
        """Execute tools based on intent."""
        results = []
        # Tool execution logic for future implementation
        # AR1: Placeholder for tool integration
        return results

    def _build_prompt(self, user_request: str, memory_context: str, 
                     tool_results: List[Dict], conversation_history: List[Dict]) -> str:
        """
        Build the complete prompt for the LLM.
        Follows Prompt Management principles from Chapter 13.
        """
        parts = []

        # System Prompt
        parts.append(f"<system>\n{self.system_prompt}\n</system>")

        # Memory Context (if available)
        if memory_context:
            parts.append(f"<memory>\n{memory_context}\n</memory>")

        # Conversation History
        if conversation_history:
            parts.append("<conversation_history>")
            for msg in conversation_history[-5:]:  # Last 5 messages for AR1
                role = msg.get("role", "user")
                content = msg.get("content", "")
                parts.append(f"{role}: {content}")
            parts.append("</conversation_history>")

        # Tool Results (if any)
        if tool_results:
            parts.append("<tool_results>")
            for result in tool_results:
                parts.append(json.dumps(result))
            parts.append("</tool_results>")

        # User Request
        parts.append(f"<user>\n{user_request}\n</user>")
        parts.append("<assistant>")

        return "\n\n".join(parts)

    def _call_provider(self, prompt: str) -> str:
        """Call the provider manager to get LLM response."""
        try:
            # Get active provider from provider manager
            provider = self.provider_manager.get_active_provider()
            if not provider:
                raise RuntimeError("No active provider found")

            # Call provider with prompt
            response = provider.generate(prompt)
            return response

        except Exception as e:
            raise RuntimeError(f"Provider call failed: {str(e)}")

    def _update_memory(self, user_request: str, response: str):
        """Update memory with conversation."""
        try:
            if self.memory_manager:
                self.memory_manager.save_conversation(user_request, response)
        except Exception as e:
            print(f"[Memory Warning] Could not update memory: {e}")


class AgentManager:
    """
    Central controller for all agents in IRON BOLT.
    Single Responsibility: Manage agent lifecycle and routing.
    """

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.default_agent: Optional[str] = None
        self.provider_manager = None
        self.memory_manager = None
        self.tool_manager = None

    def set_dependencies(self, provider_manager=None, memory_manager=None, tool_manager=None):
        """Set system dependencies (managers)."""
        self.provider_manager = provider_manager
        self.memory_manager = memory_manager
        self.tool_manager = tool_manager

    def register_agent(self, agent: BaseAgent, is_default: bool = False):
        """Register an agent."""
        self.agents[agent.name] = agent
        if is_default:
            self.default_agent = agent.name
        print(f"[AgentManager] Registered agent: {agent.name}")

    def create_general_agent(self) -> GeneralAgent:
        """Factory method to create the default general agent."""
        agent = GeneralAgent(
            provider_manager=self.provider_manager,
            memory_manager=self.memory_manager,
            tool_manager=self.tool_manager
        )
        return agent

    def get_agent(self, name: Optional[str] = None) -> BaseAgent:
        """Get an agent by name or return default."""
        if name and name in self.agents:
            return self.agents[name]

        if self.default_agent and self.default_agent in self.agents:
            return self.agents[self.default_agent]

        raise RuntimeError("No agent available. Please register an agent first.")

    def process(self, user_request: str, agent_name: Optional[str] = None, 
                conversation_history: List[Dict] = None, **kwargs) -> Dict[str, Any]:
        """
        Main entry point for processing requests through agents.
        This is what main.py should call.
        """
        agent = self.get_agent(agent_name)
        return agent.process_request(user_request, conversation_history, **kwargs)

    def list_agents(self) -> List[str]:
        """List all registered agents."""
        return list(self.agents.keys())


# Singleton instance for global access
_agent_manager_instance = None

def get_agent_manager() -> AgentManager:
    """Get or create the global agent manager instance."""
    global _agent_manager_instance
    if _agent_manager_instance is None:
        _agent_manager_instance = AgentManager()
    return _agent_manager_instance
