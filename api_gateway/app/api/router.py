from fastapi import APIRouter, Depends
from app.api.schemas import GenerateRequest, GenerateResponse, UsageResponse
from app.domain.models import PromptEntity
from app.api.dependencies import get_generate_usecase, get_usage_usecase
from app.usecases.generate_usecase import GenerateUseCase
from app.usecases.get_usage_usecase import GetUsageUseCase

router = APIRouter()

@router.post("/generate", response_model=GenerateResponse)
async def generate_response(
    req: GenerateRequest, 
    usecase: GenerateUseCase = Depends(get_generate_usecase)
):
    # Map input to domain bounds
    domain_entity = PromptEntity(user_id=req.user_id, prompt=req.prompt)
    
    # Execute orchestration
    result = await usecase.execute(domain_entity)
    
    # Map output presentation
    return GenerateResponse(
        response=result.response,
        cache_hit=result.cache_hit
    )

@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    user_id: str,
    usecase: GetUsageUseCase = Depends(get_usage_usecase)
):
    # Execute query orchestration
    result = await usecase.execute(user_id)
    
    # Map output presentation
    return UsageResponse(
        user_id=result.user_id,
        total_requests=result.total_requests,
        prompt_tokens=result.prompt_tokens,
        response_tokens=result.response_tokens,
        total_tokens=result.total_tokens,
        avg_latency_ms=result.avg_latency_ms
    )

