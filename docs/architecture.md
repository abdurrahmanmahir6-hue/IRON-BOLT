**IRON BOLT — Developer Roadmap** 

Based on Book of Iron Bolt 

# **IRON BOLT Developer Roadmap** 

Complete Phase-by-Phase Implementation Guide for Building the IRON BOLT AI Operating Framework 

**Source:** Book of Iron Bolt (175 pages) 

**Audience:** Developers & AI Engineers 

**Principle:** All content, file structures, layer order, and guidelines are taken directly from the source document. Nothing is invented. 

##### **Current Status (from source)** 

- Core project structure — Implemented 

- Configuration System — Implemented 

- Provider abstraction + Manager — Implemented (Foundation) 

- OpenAI Provider + Groq Provider — Implemented 

- Startup Validation + Runtime Config + Health Check — Implemented 

- Test infrastructure foundation — Implemented 

- Memory / Tool / Agent / Workflow / Planning — Future / Paused for next version 

Page 1  |  Strictly derived from source document  |  For Developers Only 

**IRON BOLT — Developer Roadmap** 

Based on Book of Iron Bolt 

## **1. Vision & Purpose (Source: Chapter 1)** 

IRON BOLT is not merely another AI Chatbot. It is a modular AI operating framework in which multiple Large Language Models (LLM), Tools, Memory System and Intelligent Agents can work together inside the same architecture. 

The primary goal is to create a production-ready foundation on which Personal AI Assistant, Autonomous Agent, Coding Assistant, Research Assistant, Automation System or a complete AI Operating System can later be built. 

Every component must remain loosely coupled so that changing one component does not require changing the entire system. 

#### **Long-term Vision** 

- Multiple AI Providers can be used. 

- Model can be changed at runtime. 

- Tool execution is managed safely. 

- AI can use its own Memory. 

- Different Agents use the same Framework. 

- Future Multi-Agent Collaboration becomes possible. 

- Production-scale applications can be built. 

Therefore IRON BOLT is not a single chatbot; it is a complete foundation for building AI applications. 

## **2. Design Philosophy & Principles (Source: Chapters 1, 2, 4)** 

#### **Core Philosophy** 

##### **Build a small but solid foundation first. Expand only after the foundation becomes stable.** 

Instead of implementing hundreds of features at the beginning, IRON BOLT focuses on creating reliable building blocks. Every new system should be built on top of an already tested and stable system. 

#### **Key Principles (must be followed by every developer)** 

**Modular** — Every module stays independent. Provider, Memory, Tool, Agent, API are all independent components. Maintenance becomes easy and adding new features becomes much easier. 

**Provider Independent** — The system never depends on a single AI Provider. OpenAI, Gemini, Groq, Ollama, OpenRouter or any future Provider all use the same interface. This architecture avoids vendor lock-in. 

**Scalable** — The same architecture works from small projects to enterprise-level applications. Even when the number of components grows, the system remains maintainable. 

**Extensible** — Every layer is designed so that adding a new module requires very little change to existing code. Adding new Provider, Tool, Memory Backend or Agent is a natural capability of the framework. 

**Testable** — Every component can be tested independently. Unit Test, Integration Test and future End-to-End Test are considered part of the architecture. 

**Production First** — From the start of development, production-quality architecture is followed. Temporary solutions or quick hacks that destroy future architecture are not used. Code readability, maintainability and reliability always receive priority. **Single Responsibility** — Every module has one clear responsibility. ProviderManager manages providers. ToolManager manages tools. MemoryManager manages memory. AgentEngine controls agent execution. None of these should contain the logic of another component. 

**Configuration Over Hardcoding** — System behaviour comes from configuration (API Keys, Default Provider, Default Model, Timeouts, Retry Limits, Feature Flags) instead of hardcoded values. Changing configuration should not require changing source code. 

**Expand Without Breaking** — New features should extend the project instead of modifying stable code. Prefer adding new modules / implementations. Avoid rewriting stable components. 

**Start Simple, Scale Later** — If a feature is not required today, it should not be implemented today. Avoid unnecessary complexity and over-engineering. 

**Test Before Trust** — Every important component is tested before it becomes part of the stable architecture. A feature is considered complete only after it works reliably under testing. 

**Documentation First** — Before implementing a major system, its purpose, architecture, responsibilities and expected behaviour should be clearly documented. 

Page 2  |  Strictly derived from source document  |  For Developers Only 

**IRON BOLT — Developer Roadmap** 

Based on Book of Iron Bolt 

## **3. Strict Architecture Rules (Source: Chapter 2)** 

IRON BOLT follows Layered Architecture. The whole system is divided into independent layers. Each layer has a specific responsibility and no layer takes the responsibility of another layer. Connections between layers happen through interfaces, not direct module dependency. 

#### **Import / Dependency Rules (enforced)** 

- I core.* → any layer may import it. 

- II provider.* → only Assistant (or the layer that needs it) may use it. 

- II memory.* → only when needed by Assistant. 

- II tools.* → only when needed by Assistant. 

- I Memory must never import Tool. 

- I Tool must never import Provider. 

- I Provider must never import Memory. 

- Layer dependencies are strictly one-way. 

- No circular dependency is allowed. 

- Shared logic is never copied; it lives in a Common Module. 

- Every Module has a Single Responsibility. 

Result of these rules: code stays clean, debugging is easy, testing is easy, adding features is easy, and changing one component does not break the whole system. 

## **4. High-Level Request Flow (Source: Chapter 2)** 

User → Iron Bolt (AI Assistant) → Assistant Runtime → Planning / Thinking / Reasoning → (Tool System | Memory System | Knowledge System) → Provider Manager → (OpenAI | Gemini | Groq) → AI Models (default = gpt-oss-120b) → Response → User 

IRON BOLT as Assistant manages the whole conversation. Assistant Runtime manages request execution. Planner / Reasoning decides what to do. Memory / Knowledge / Tools supply information or capability as needed by the Planner. Provider Manager decides which AI Provider is used. The Provider talks to the concrete AI service. The AI Model performs final reasoning and response generation. 

Page 3  |  Strictly derived from source document  |  For Developers Only 

**IRON BOLT — Developer Roadmap** 

Based on Book of Iron Bolt 

## **5. Official Implementation Order (Source: Chapter 5)** 

IRON BOLT is built bottom-up. Foundation first, then higher layers. A strong Core Architecture is more important than new features. 

**1. Core Layer** — Foundation — all other layers depend on it 

**2. Provider System** — Unified interface to any LLM 

**3. Memory System** — Conversation + long-term context 

**4. Tool System** — Action layer — real-world capabilities 

**5. Agent System** — Decision / brain layer 

**6. Workflow Engine** — Multi-step sequential execution (Paused — next version) 

**7. Planning & Reasoning** — Break large problems into tasks (Paused — implement with Phase 6) 

**8. Prompt Management** — Structured, reusable prompts (Paused) 

**9. Plugin & MCP System** — Extensibility without changing core (Paused) 

**10. Security & Permissions** — Control what AI is allowed to do (Paused) 

**11. Execution Flow** — End-to-end request pipeline (Paused) 

**12. Architecture Refinement** — Performance, monitoring, optimisation (Paused) 

**13. Future Expansion** — Multi-agent, distributed, self-improvement, etc. (Future) 

### **PHASE 1 — Core Layer / Core Foundation** 

##### **Purpose (Source: Chapters 3 & 6)** 

Core Layer is the heart / kernel of IRON BOLT. Like the kernel of an OS, every other module depends on it. It does not implement AI features; it provides stable, predictable, reusable infrastructure so that Provider, Memory, Tool, Agent etc. never depend directly on each other. 

#### **Why it exists** 

If every component reads configuration, creates providers, handles errors, logs and validates by itself, the same code is written repeatedly → duplication, bugs, hard maintenance, risk when changing large parts. Core solves this by giving common infrastructure. 

#### **Responsibilities** 

- Project Configuration management 

- Runtime Environment preparation 

- Provider Lifecycle management 

- System Startup Validation 

- Common Base Classes 

- Shared Utilities 

- Framework Initialization 

- Foundation that connects all modules 

#### **Required Files / Directory Structure (from source)** 

```
core/
|-- config.py
|-- runtime.py
|-- exceptions.py
|-- logger.py
|-- validation.py
|-- startup_validation.py
|-- constants.py
|-- context.py
|-- registry.py          # future
|-- events.py            # future
|-- metrics.py           # future
|-- lifecycle.py         # future
`-- utils.py
```

#### **Guidelines for Core Layer (must follow)** 

Page 4  |  Strictly derived from source document  |  For Developers Only 

**IRON BOLT — Developer Roadmap** 

Based on Book of Iron Bolt 

- Core must never depend on Tool Layer, Agent Layer or Memory Layer. 

- Core uses only Python Standard Library + approved shared libraries. 

- All other layers may use Core; Core never uses them. Dependency direction is always one-way. 

- No component may read Environment Variables directly; everything goes through Configuration System. 

- Business logic never lives in Core. Core only provides infrastructure. 

- Startup Validation must fail safely and show a clear error if configuration, API keys, dependencies or providers are not ready. 

#### **Current Implementation Status (from source)** 

Implemented: Project Structure, Configuration System, Provider Manager (foundation), Provider Base Architecture, Runtime Configuration, Startup Validation, Provider Health Check, Unit Test Foundation. 

_Future inside Core: Unified Exception System, Logging Framework, Lifecycle Manager, Component Registry, Event System, Metrics, Dependency Injection, Performance Monitoring._ 

### **PHASE 2 — Provider System** 

##### **Purpose (Source: Chapter 7)** 

Provider System is the layer through which the whole framework communicates with any Large Language Model. IRON BOLT itself is not an AI model; it is an AI Runtime Framework. Therefore it needs a Provider to actually generate answers. The Provider System gives a single unified interface to OpenAI, Groq, Gemini, Claude, Ollama, local LLMs or any future provider. 

#### **Why it exists** 

If OpenAI or Groq API calls were written directly in hundreds of places, changing provider later would require rewriting the whole project. That is unacceptable for production software. Provider Layer is the abstraction that prevents vendor lock-in. 

#### **Responsibilities** 

- Create connection to AI Model 

- Authentication with API Key 

- Select which model to use 

- Send prompt / receive response 

- Error handling 

- Health Check 

- Provide available model list 

- Future: Retry, Streaming, Usage & Cost tracking 

#### **Required Files / Directory Structure (from source)** 

```
providers/
```

- `|-- __init__.py` 

- `|-- base.py                 # Abstract Base Provider (must be followed by every provider)` 

- `|-- manager.py              # Provider Manager - central controller` 

- `|-- openai_provider.py` 

- `|-- groq_provider.py        # currently the primary / default provider` 

- ``-- (future providers)` 

#### **Guidelines for Provider System** 

- Framework never talks directly to OpenAI Provider or Groq Provider. Everything goes through Provider Manager. 

- Every concrete provider (OpenAI, Groq, Gemini…) must implement the Base Provider interface. 

- Provider Layer never contains Business Logic. 

- Default model currently used in the project: gpt-oss-120b (via Groq). 

- Provider Manager is responsible for: Register, Initialize, Select Default, Return Active, Change, Health Check, future Multi-Provider management. 

- This Phase depends completely on the Core Layer. 

#### **Current Status** 

Page 5  |  Strictly derived from source document  |  For Developers Only 

**IRON BOLT — Developer Roadmap** 

Based on Book of Iron Bolt 

Foundation is complete: Provider Interface, Provider Manager, Base Provider, OpenAI Provider, Groq Provider, Startup Validation, Runtime Configuration, Health Check. 

Page 6  |  Strictly derived from source document  |  For Developers Only 

**IRON BOLT — Developer Roadmap** 

Based on Book of Iron Bolt 

### **PHASE 3 — Memory System** 

##### **Purpose (Source: Chapters 2, 5, 8)** 

Memory System lets the AI remember important information across conversations instead of starting every conversation completely fresh. Ordinary LLMs are limited to the current context window; once the conversation ends or the limit is exceeded the information is lost. Memory System solves this so that AI can provide a more personal, continuous and intelligent experience. 

#### **Responsibilities** 

- Store important information 

- Retrieve information when needed 

- Discard unnecessary information 

- Update memory 

- Avoid duplicate memory 

- Search memory 

- Delete memory 

- Identify important information from conversation 

- Keep memory separate per user 

- Supply memory to other components 

#### **Types of Memory (from source)** 

- **User Memory** — long-term (name, language, preferences, goals…) 

- **Conversation Memory** — current conversation flow, recent decisions, temporary context 

- Session Memory, Long-term Memory, Vector Memory, User Preferences are also planned. 

#### **Required Files / Directory Structure (from source)** 

```
memory/
|-- __init__.py
|-- manager.py              # MemoryManager
```

```
|-- models.py
|-- storage.py
|-- retrieval.py
```

```
|-- update.py
|-- decision.py
|-- config.py
|-- exceptions.py
|-- utils.py
|-- base_memory.py          # (earlier structure)
|-- short_term.py
```

- `|-- long_term.py` 

- ``-- conversation.py` 

```
data/
```

```
`-- memory.json             # example storage
```

#### **Guidelines for Memory System** 

- Memory System itself never makes decisions. It only stores and supplies information. 

- Memory and Knowledge are not the same thing. Memory = AI’s experience. Knowledge = AI’s external knowledge base. 

- Memory System uses Provider System when it needs to build context. 

- All tools and agents access memory only through MemoryManager. 

- This Phase depends on Core Layer + Provider System. 

### **PHASE 4 — Tool System** 

##### **Purpose (Source: Chapters 2, 5, 10)** 

Tool System is the Action Layer. An AI model can only think and generate text; it cannot perform real-world actions (read a file, run Python, search the web, call an API, etc.). Tool System gives IRON BOLT the ability to perform those real actions. 

Page 7  |  Strictly derived from source document  |  For Developers Only 

**IRON BOLT — Developer Roadmap** 

Based on Book of Iron Bolt 

#### **Responsibilities** 

- Register tools 

- Store tool metadata 

- Execute tools safely 

- Validate tool input 

- Collect tool output 

- Monitor execution status 

- Handle errors 

- Return results to Agent System 

#### **Required Files / Directory Structure (from source)** 

```
tools/
```

```
|-- tool_manager.py
```

```
|-- base_tool.py            # every tool must implement this interface
```

- `|-- registry.py` 

- `|-- validator.py` 

- `|-- executor.py` 

- `|-- result.py` 

- `|-- permissions.py` 

```
|-- python_tool.py
```

- `|-- file_tool.py` 

- `|-- search_tool.py` 

- `|-- browser_tool.py` 

- `|-- calculator_tool.py` 

- `|-- terminal_tool.py` 

- `|-- api_tool.py` 

```
`-- ...
```

#### **Guidelines for Tool System** 

- Agent never calls TerminalTool() or PythonTool() directly. Always: tool_manager.execute("terminal", command) 

- Tool System itself never decides which tool to use or when. That decision belongs only to Agent System. 

- Every tool implements the Base Tool interface (name, description, required parameters, execute method, result). 

- ToolManager responsibilities: register, find, execute, enable/disable, permission check. 

- This Phase depends on Core Layer + Memory System. 

#### **Current Status** 

_In the current AR1 version only the foundation and the most necessary tools will be added. Not every tool is implemented at once._ 

### **PHASE 5 — Agent System** 

##### **Purpose (Source: Chapters 2, 5, 9)** 

Agent System is the Decision Layer / “Brain” of IRON BOLT. Provider only talks to models, Memory only stores/retrieves, Tools only execute actions. Agent System decides: does this request need a tool? does it need memory? which model should be used? what is the next action? It coordinates all capabilities into one intelligent assistant. 

#### **Responsibilities** 

- Analyse user request 

- Understand intent 

- Use Memory System when needed 

- Call ToolManager when a tool is required 

- Use Provider Manager to choose the right model 

- Complete multi-step tasks when necessary 

- Combine results from different components 

- Generate the final response for the user 

#### **Components planned (from source)** 

- Agent 

- Task Execution Loop 

Page 8  |  Strictly derived from source document  |  For Developers Only 

**IRON BOLT — Developer Roadmap** 

Based on Book of Iron Bolt 

- Decision Controller 

- Agent State 

- Goal Tracking 

- Response Generator 

#### **Guidelines for Agent System** 

- Agent System is currently listed as Future Implementation in the early chapters; it becomes active after Core + Provider + Memory + Tool are ready. 

- Dependency: Provider + Memory + Tool. 

- Agent never imports tools or providers directly; it always goes through the respective Managers. 

Page 9  |  Strictly derived from source document  |  For Developers Only 

**IRON BOLT — Developer Roadmap** 

Based on Book of Iron Bolt 

### **PHASES 6–13 — Future / Paused (Source: Chapter 5)** 

The following phases are explicitly marked in the source document as “Pause. next version” or “Future”. They must not be implemented until the earlier phases are stable. The architecture is already designed so that they can be added later without major restructuring. 

#### **Phase 6 — Workflow Engine** 

Execute multiple steps sequentially. Components: Workflow Definition, Workflow Runner, Step Executor, Conditional Execution, Retry, Workflow Context. Real tasks are rarely finished in one step. 

#### **Phase 7 — Planning & Reasoning** 

Break a large problem into smaller tasks. Components: Planner, Goal Analyzer, Task Breakdown, Dependency Planning, Reasoning Controller, Execution Strategy. To be implemented together with Phase 6. 

#### **Phase 8 — Prompt Management** 

Make prompts structured and reusable. Components: Prompt Templates, Prompt Builder, System Prompt, Dynamic Prompt Injection, Prompt Versioning. 

#### **Phase 9 — Plugin & MCP System** 

Extend capability without changing core code. Components: Plugin Loader, Plugin Registry, Plugin Lifecycle, MCP Client, MCP Server Communication. 

#### **Phase 10 — Security & Permission** 

Control what the AI is allowed to do. Components: Permission System, Tool Permission, Provider Permission, File Permission, User Confirmation, Security Policies. Critical for autonomous AI. 

#### **Phase 11 — Execution Flow** 

Define the complete path of a user request from start to finish. Components: Request Pipeline, Context Pipeline, Tool Pipeline, Response Pipeline. After this phase the full request flow becomes stable. 

#### **Phase 12 — Architecture Refinement** 

Raise the whole system to production quality: Performance, Scalability, Caching, Monitoring, Testing, Optimization, Documentation. Focus is on strengthening existing architecture, not adding new features. 

#### **Phase 13 — Future Expansion** 

After the production version is complete: Multi-Agent Collaboration, Distributed Execution, Advanced Planning, Long-Term Knowledge System, Self Improvement, Learning Pipeline, Cloud Deployment, Team Collaboration, Visual Workflow Builder, Enterprise Features. 

## **6. Architectural Layers Summary (Source: Chapter 2)** 

**Foundation Layer** — Configuration System, Settings, Validation, Startup Logic, Common Utilities, Base Classes. All other layers depend on it. 

**Provider Layer** — Talks only to AI providers. Responsibilities: send model request, receive response, authentication, health check, runtime model selection. Never contains business logic. 

**Agent Layer** — The “Brain”. Decides whether a tool is needed, whether memory is needed, which model to use, what the next action is. Currently Future Implementation. 

**Tool Layer** — External world interaction (file, calculator, search, python, database, email, browser…). Always accessed through ToolManager. 

**Memory Layer** — Short-term and long-term storage of AI experience. Managed by MemoryManager. 

**Knowledge Layer** — External knowledge (documents, PDF, database, vector store, knowledge base, retrieval). Distinct from Memory. 

## **7. Non-Negotiable Rules for Every Developer** 

1. Follow the official Implementation Order. Do not jump ahead to later phases. 

Page 10  |  Strictly derived from source document  |  For Developers Only 

**IRON BOLT — Developer Roadmap** 

Based on Book of Iron Bolt 

2. Never invent new architecture that contradicts the layered rules. 

3. Never create circular dependencies. 

4. Never let one layer perform the responsibility of another layer. 

5. All communication between layers must go through public interfaces / Managers. 

6. Configuration always comes from the Configuration System, never hard-coded or read directly from environment. 

7. Write documentation of purpose, architecture, responsibilities and expected behaviour before implementing a major system. 

8. Test every important component before it becomes part of the stable architecture. 

9. Prefer extension over modification of already stable code. 

10. Keep every module removable / replaceable without affecting the rest of the system. 

_This roadmap is a pure extraction and organisation of the content that already exists in the Book of Iron Bolt. It is intended to be the single practical guide a developer needs to know what to build, in what order, with which files, and under which architectural constraints._ 

End of IRON BOLT Developer Roadmap 

Page 11  |  Strictly derived from source document  |  For Developers Only 

