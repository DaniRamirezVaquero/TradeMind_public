
from pydantic import BaseModel
from typing import Optional
from datetime import date

class DeviceInfo(BaseModel):
    brand: Optional[str] = ""
    model: Optional[str] = ""
    storage: Optional[str] = ""
    has_5g: Optional[bool] = None
    release_date: Optional[date] = None
    grade: Optional[str] = "C"
    estimated_price: Optional[float] = None

class BuyingInfo(BaseModel):
    budget: Optional[float] = None
    brand_preference: Optional[str] = ""
    min_storage: Optional[int] = None
    grade_preference: Optional[str] = ""
    