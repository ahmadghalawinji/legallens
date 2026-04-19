from pydantic import BaseModel


class AnalyzeResponse(BaseModel):
    task_id: str
    message: str = "Analysis started"
