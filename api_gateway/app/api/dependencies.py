from fastapi import Request
from app.usecases.generate_usecase import GenerateUseCase
from app.infrastructure.telemetry_repository import TelemetryRepository
from app.usecases.get_usage_usecase import GetUsageUseCase

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

def get_usage_usecase(request: Request) -> GetUsageUseCase:
    """
    Dependency Provider for telemetry usage querying.
    """
    state = request.app.state
    telemetry_repo = TelemetryRepository(state.db_pool)
    return GetUsageUseCase(telemetry_repo)

