import os
import time
import asyncio
from litellm import acompletion
from flashrank import Ranker, RerankRequest as FlashRankRerankRequest
from app.domain.models import PromptEntity, ResponseEntity, TelemetryData
from app.infrastructure.vector_engine import VectorEngine
from app.infrastructure.cache_repository import CacheRepository
from app.infrastructure.event_broker import EventBroker

class RerankRequest(FlashRankRerankRequest):
    """
    Custom subclass of FlashRank's RerankRequest to explicitly support 
    max_no_of_results in a python-safe manner.
    """
    def __init__(self, query=None, passages=None, max_no_of_results=None):
        super().__init__(query=query, passages=passages)
        self.max_no_of_results = max_no_of_results

# Initialize the FlashRank Ranker once at the module level to avoid initialization overhead
ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2", cache_dir="/app/.flashrank_cache")

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
        
        # 2. Perform Hybrid Search in Redis cache engine (returns top 5 candidates)
        candidates = await self.cache_repo.search_similar(entity.prompt, embedding)
        
        prompt_tokens = len(entity.prompt.split())
        response_tokens = 0
        cache_hit = False
        response_text = ""

        if candidates:
            # Format passages for FlashRank reranking
            passages = [
                {
                    "id": str(i),
                    "text": candidate["prompt"],
                    "response": candidate["response"],
                    "vector_score": candidate["vector_score"]
                }
                for i, candidate in enumerate(candidates)
            ]
            
            # Execute rerank request
            rerank_request = RerankRequest(query=entity.prompt, passages=passages, max_no_of_results=1)
            reranked_results = ranker.rerank(rerank_request)
            
            # Evaluate the top result
            if reranked_results:
                top_result = reranked_results[0]
                top_score = top_result.get("score", 0.0)
                
                # Check cross-encoder relevance threshold of 0.88
                if top_score >= 0.88:
                    cache_hit = True
                    response_text = top_result["response"]
                    response_tokens = len(response_text.split())

        if not cache_hit:
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
