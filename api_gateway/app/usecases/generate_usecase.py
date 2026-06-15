import os
import time
import asyncio
from litellm import acompletion
from app.domain.models import PromptEntity, ResponseEntity, TelemetryData
from app.infrastructure.vector_engine import VectorEngine
from app.infrastructure.cache_repository import CacheRepository
from app.infrastructure.event_broker import EventBroker

class GenerateUseCase:
    """
    Orchestrates the caching logic and external routing requests.
    Strictly isolated from HTTP dependencies.
    """
    def __init__(
        self, 
        vector_engine: VectorEngine, 
        cache_repo: CacheRepository, 
        event_broker: EventBroker
    ):
        self.vector_engine = vector_engine
        self.cache_repo = cache_repo
        self.event_broker = event_broker
        self.llm_model = os.getenv("LLM_MODEL", "gemini/gemini-1.5-flash")

    async def execute(self, entity: PromptEntity) -> ResponseEntity:
        start_time = time.time()
        
        # 1. Vectorize the prompt.
        embedding = await self.vector_engine.encode(entity.prompt)
        
        # 2. Perform Cosine Similarity search in Redis cache engine
        cached_response = await self.cache_repo.search_similar(embedding, threshold=0.95)
        
        prompt_tokens = len(entity.prompt.split())
        response_tokens = 0

        if cached_response:
            cache_hit = True
            response_text = cached_response
            response_tokens = len(response_text.split())
        else:
            cache_hit = False
            # 3. Call LLM Generator via LiteLLM
            api_key = VectorEngine.get_api_key(self.llm_model)
            response = await acompletion(
                model=self.llm_model,
                messages=[{"role": "user", "content": entity.prompt}],
                api_key=api_key
            )
            response_text = response.choices[0].message.content or ""
            
            # Try to get token counts from LiteLLM usage info, falling back to split method
            if hasattr(response, 'usage') and response.usage:
                prompt_tokens = getattr(response.usage, 'prompt_tokens', prompt_tokens)
                response_tokens = getattr(response.usage, 'completion_tokens', len(response_text.split()))
            else:
                response_tokens = len(response_text.split())
            
            # 4. Save newly generated entry seamlessly back into cache DB
            await self.cache_repo.save(entity.prompt, response_text, embedding)

        latency_ms = int((time.time() - start_time) * 1000)

        # 5. Hydrate Telemetry Schema
        telemetry = TelemetryData(
            user_id=entity.user_id,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
            latency_ms=latency_ms,
            cache_hit=cache_hit
        )
        
        # 6. Publish telemetry via Kafka asynchronously
        # Creating a detached task ensures the HTTP connection returns immediately.
        asyncio.create_task(
            self.event_broker.publish_telemetry("gateway_telemetry", telemetry.__dict__)
        )

        return ResponseEntity(response=response_text, cache_hit=cache_hit)
