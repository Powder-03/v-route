from fastapi import Request
from app.usecases.generate_usecase import GenerateUseCase

def get_generate_usecase(request: Request) -> GenerateUseCase:
    """
    Dependency Provider.
    Extracts initialized infrastructure instances from the application state layer.
    """
    state = request.app.state
    return GenerateUseCase(
        vector_engine=state.vector_engine,
        cache_repo=state.cache_repo,
        event_broker=state.event_broker
    )
