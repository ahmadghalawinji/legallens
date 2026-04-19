from fastapi import APIRouter

router = APIRouter()


@router.post("/analyze")
async def analyze_contract() -> dict:
    """Analyze a contract for risks. Not yet implemented."""
    return {"status": "not implemented", "data": None, "errors": None, "metadata": None}
