from fastapi import APIRouter, HTTPException

from app.models.schemas import ParseRequest, ParseResult
from app.services.parser import enrich_parse_result, parse_url

router = APIRouter()


@router.post("/api/parse", response_model=ParseResult)
async def parse(req: ParseRequest) -> ParseResult:
    try:
        result = parse_url(req.url)
        return await enrich_parse_result(result)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
