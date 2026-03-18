"""HTML report generation route."""

from fastapi import APIRouter

from generate.schemas import GenerateReportRequest, GenerateReportResponse
from generate.service import GenerateService

router = APIRouter(prefix="/generate", tags=["Generate"])


@router.post(
    "",
    response_model=GenerateReportResponse,
    summary="Generate HTML report from config and data",
)
async def generate_report(body: GenerateReportRequest) -> GenerateReportResponse:
    service = GenerateService()
    html = service.generate(body.config, body.components, body.all_data)
    return GenerateReportResponse(html=html)
