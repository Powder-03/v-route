from app.domain.models import UsageSummary
from app.infrastructure.telemetry_repository import TelemetryRepository

class GetUsageUseCase:
    """
    Orchestrates retrieving user usage telemetry.
    Strictly isolated from HTTP dependencies.
    """
    def __init__(self, telemetry_repo: TelemetryRepository):
        self.telemetry_repo = telemetry_repo

    async def execute(self, user_id: str) -> UsageSummary:
        return await self.telemetry_repo.get_user_usage(user_id)
