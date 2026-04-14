from fastapi import APIRouter, Depends
from app.api.schemas import GenerateRequest, GenerateResponse
from app.domain.models import PromptEntity
from app.api.dependencies import get_generate_usecase
from app.usecases.generate_usecase import GenerateUseCase

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
