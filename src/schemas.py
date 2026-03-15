from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date

class WorkPackage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int
    subject: str
    status: str
    startDate: Optional[date] = None
    dueDate: Optional[date] = None

class ProjectSummary(BaseModel):
    active: List[WorkPackage] = []
