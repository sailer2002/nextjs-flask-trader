# app/models.py
from pydantic import BaseModel

class TradingSignal(BaseModel):
    symbol: str
    direction: str
    is_test: bool
    position_size: float

