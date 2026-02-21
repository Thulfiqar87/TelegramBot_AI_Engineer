from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import date

class WorkPackage(BaseModel):
    id: int
    subject: str
    status: str
    startDate: Optional[date] = None
    dueDate: Optional[date] = None
    
    class Config:
        arbitrary_types_allowed = True

class ProjectSummary(BaseModel):
    active: List[WorkPackage] = []
