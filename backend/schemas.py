from pydantic import BaseModel

class DecisionIn(BaseModel):
    approved: bool
