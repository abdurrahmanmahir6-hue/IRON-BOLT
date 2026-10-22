# ============================================
# EXISTING IMPORTS (তোমার আগের imports)
# ============================================
from core.config import Config
from core.startup_validation import validate_startup_environment
from providers.provider_manager import ProviderManager
from providers.registry import ProviderRegistry
from providers import GroqProvider, OpenAIProvider, GeminiProvider, ProviderConfig


# ============================================
# NEW IMPORTS (নতুন layers)
# ============================================
from agents.agent_manager import get_agent_manager
from tools.tool_manager import get_tool_manager, CalculatorTool, FileTool
from memory.memory_manager import get_memory_manager
from workflow.workflow_engine import get_workflow_engine
from database.database_manager import get_database_manager
from memory.models import utc_now


class IronBolt:
    def __init__(self):
        self.config = None
        self.provider_manager = None
        self.agent_manager = None
        self.tool_manager = None
        self.memory_manager = None
        self.workflow_engine = None
        self.db_manager = None
        self.initialized = False

    def initialize(self):
        """Initialize all IRON BOLT layers."""
        print("=" * 50)
        print("IRON BOLT - Initializing...")
        print("=" * 50)

        # 1. Core Layer
        self.config = validate_startup_environment()
        self.config.validate()
        print("[OK] Core Layer")

        # 2. Provider Layer
        registry = ProviderRegistry()

        groq_provider = GroqProvider()
        groq_key = self.config.providers.groq_api_key.get_secret_value() if self.config.providers.groq_api_key else None
        if groq_key:
            try:
                groq_provider.initialize(ProviderConfig(
                    api_key=groq_key,
                    model=self.config.providers.model or "openai/gpt-oss-120b",
                    extra={"timeout_seconds": self.config.providers.timeout_seconds}
                ))
            except Exception as e:
                print(f"[Warning] GroqProvider initialization failed: {e}")
        registry.register("groq", groq_provider)

        openai_provider = OpenAIProvider()
        openai_key = self.config.providers.openai_api_key.get_secret_value() if self.config.providers.openai_api_key else None
        if openai_key:
            try:
                openai_provider.initialize(ProviderConfig(
                    api_key=openai_key,
                    model="gpt-4o-mini",
                    extra={"timeout_seconds": self.config.providers.timeout_seconds}
                ))
            except Exception as e:
                print(f"[Warning] OpenAIProvider initialization failed: {e}")
        registry.register("openai", openai_provider)

        gemini_provider = GeminiProvider()
        gemini_key = self.config.providers.gemini_api_key.get_secret_value() if self.config.providers.gemini_api_key else None
        if gemini_key:
            try:
                gemini_provider.initialize(ProviderConfig(
                    api_key=gemini_key,
                    model="gemini-2.0-flash",
                    extra={"timeout_seconds": self.config.providers.timeout_seconds}
                ))
            except Exception as e:
                print(f"[Warning] GeminiProvider initialization failed: {e}")
        registry.register("gemini", gemini_provider)

        self.provider_manager = ProviderManager(registry)
        print("[OK] Provider Layer")

        # 3. Database Layer (NEW)
        self.db_manager = get_database_manager()
        self.db_manager.initialize()
        print("[OK] Database Layer")

        # 4. Memory Layer (NEW)
        self.memory_manager = get_memory_manager()
        print("[OK] Memory Layer")

        # 5. Tool Layer (NEW)
        self.tool_manager = get_tool_manager()
        self._register_default_tools()
        print("[OK] Tool Layer")

        # 6. Agent Layer (NEW - এটাই main fix!)
        self.agent_manager = get_agent_manager()
        self.agent_manager.set_dependencies(
            provider_manager=self.provider_manager,
            memory_manager=self.memory_manager,
            tool_manager=self.tool_manager
        )
        general_agent = self.agent_manager.create_general_agent()
        self.agent_manager.register_agent(general_agent, is_default=True)
        print("[OK] Agent Layer")

        # 7. Workflow Layer (NEW)
        self.workflow_engine = get_workflow_engine(
            tool_manager=self.tool_manager,
            provider_manager=self.provider_manager,
            memory_manager=self.memory_manager
        )
        print("[OK] Workflow Layer")

        self.initialized = True
        print("=" * 50)
        print("IRON BOLT - Ready")
        print("=" * 50)

    def _register_default_tools(self):
        """Register default tools."""
        self.tool_manager.register_tool(CalculatorTool())
        self.tool_manager.register_tool(FileTool())

    def chat(self, message: str) -> str:
        """Process a user message and return response."""
        if not self.initialized:
            raise RuntimeError("IRON BOLT not initialized. Call initialize() first.")

        # Agent Manager দিয়ে process করো
        request_timestamp = utc_now()
        result = self.agent_manager.process(
            user_request=message,
            conversation_history=self.memory_manager.get_conversation_history(),
            request_timestamp=request_timestamp,
        )

        if result["success"]:
            return result["response"]
        else:
            return f"Error: {result.get('error', 'Unknown error')}"

    def shutdown(self):
        """Shutdown all layers gracefully."""
        if self.db_manager:
            self.db_manager.shutdown()
        print("IRON BOLT - Shutdown complete")


# Global instance
_iron_bolt = None

def get_iron_bolt():
    global _iron_bolt
    if _iron_bolt is None:
        _iron_bolt = IronBolt()
    return _iron_bolt


# ============================================
# MAIN ENTRY POINT
# ============================================
if __name__ == "__main__":
    bot = get_iron_bolt()
    bot.initialize()

    print("\nIRON BOLT Chat (type 'exit' to quit)\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ["exit", "quit", "bye"]:
                break
            if not user_input:
                continue

            response = bot.chat(user_input)
            print(f"\nIron Bolt: {response}\n")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    bot.shutdown()
    print("\nGoodbye!")
