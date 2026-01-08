from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional

class Customer(BaseModel):
    name: str
    email: Optional[str] = None

class Part(BaseModel):
    name: str
    part_number: str
    revision: str = "A"

class Process(BaseModel):
    printer: str
    resin: str
    part_volume_ml: float = Field(gt=0)
    qty: int = Field(ge=1)
    print_hours: float = Field(gt=0)

class Options(BaseModel):
    wash_cure: bool = True
    support_removal: bool = True
    finishing: bool = False
    packaging: bool = True
    docs_packet: bool = False
    inspection: bool = False
    expedite_multiplier: float = Field(default=1.0, gt=0)

class OutsideService(BaseModel):
    description: str
    vendor_cost: float = Field(ge=0)
    markup_pct: float = Field(ge=0, le=1)

class QuoteInput(BaseModel):
    quote_id: str
    customer: Customer
    part: Part
    process: Process
    options: Options = Options()
    outside_services: List[OutsideService] = []
