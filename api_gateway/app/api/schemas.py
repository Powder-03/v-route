from pydantic import BaseModel

class GenerateRequest(BaseModel):
    user_id: str
    prompt: str

class GenerateResponse(BaseModel):
    response: str
    cache_hit: bool

class UsageResponse(BaseModel):
    user_id: str
    total_requests: int
    prompt_tokens: int
    response_tokens: int
    total_tokens: int
    avg_latency_ms: float

