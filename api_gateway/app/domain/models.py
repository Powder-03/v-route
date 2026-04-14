from dataclasses import dataclass

@dataclass
class PromptEntity:
    user_id: str
    prompt: str

@dataclass
class ResponseEntity:
    response: str
    cache_hit: bool

@dataclass
class TelemetryData:
    user_id: str
    prompt_tokens: int
    response_tokens: int
    latency_ms: int
    cache_hit: bool
