"""
Data models for offer monitoring application.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class DealItem(BaseModel):
    title: str = Field(description="The title of the deal offer")
    link: str = Field(description="The direct link/URL to the deal offer")
    target_name: str = Field(default="Deal", description="Store or brand name, e.g. Coles Gift Card or Finder")
    votes: str = Field(default="0", description="Upvotes count or deal rating string")
    coupon: Optional[str] = Field(default=None, description="Coupon code if applicable")
    submitted: str = Field(default="Just now", description="Submission timestamp or text")


class DealList(BaseModel):
    deals: List[DealItem] = Field(description="List of active deal offers found")
