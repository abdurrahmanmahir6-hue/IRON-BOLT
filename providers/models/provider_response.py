"""  
provider_response.py  
  
Canonical response contract returned by generate() / stream().  
  
Every concrete provider must translate its native SDK/API response into  
this shape. The Orchestrator only ever consumes a ProviderResponse.  
"""  
  
from dataclasses import dataclass, field  
from typing import Any, Optional  
  
  
@dataclass  
class ProviderResponse:  
    """  
    Attributes:  
        content:        Generated text (or final concatenated stream text).  
        provider_name:  Which provider produced the response (audit trail).  
        provider:       Alias for provider_name (backward compat).
        model:          Actual model that was used.  
        finish_reason:  Why generation stopped.  
        usage:          Token counts / cost information.  
        tool_calls:     Any tool / function calls returned by the model.  
        citations:      Optional source citations.  
        reasoning:      Optional chain-of-thought / reasoning traces.  
        images:         Optional generated or returned images.  
        audio:          Optional generated audio.  
        latency_ms:     Wall-clock latency of the call (milliseconds).  
        latency:        Wall-clock latency (seconds, backward compat).
        request_id:     Correlation ID for the request.
        raw:            Untouched original SDK response (debug only).  
        raw_response:   Alias for raw (backward compat).
        metadata:       Free-form extra data.  
    """  
  
    content: str  
    provider_name: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None  
    finish_reason: Optional[str] = None  
    usage: Optional[dict[str, Any]] = None  
    tool_calls: Optional[list[dict[str, Any]]] = None  
    citations: Optional[list[Any]] = None  
    reasoning: Optional[str] = None  
    images: Optional[list[Any]] = None  
    audio: Optional[Any] = None  
    latency_ms: Optional[float] = None  
    latency: Optional[float] = None
    request_id: Optional[str] = None
    raw: Any = None  
    raw_response: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)  
