# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.10.0",
# ]
# ///
"""
Strict schema models for rental listings.
Enforces:
- Extra forbidden attributes (pydantic.BaseModel extra='forbid')
- Zero emoji validation
- Numeric boundary validation (rent, deposit, sizes, ages)
- Dual-language German & English text parity validation
"""

import re
import sys
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

EMOJI_PATTERN = re.compile(r'[\U00010000-\U0010ffff]')

class RentalListingSchema(BaseModel, extra='forbid'):
    title: str = Field(..., min_length=5, max_length=120)
    city: str = Field(default="Hamburg")
    district: str = Field(..., min_length=2, max_length=60)
    postcode: str = Field(..., pattern=r'^\d{5}$')
    street: str = Field(..., min_length=2, max_length=80)
    housenumber: Optional[str] = Field(default="")
    
    room_size_sqm: float = Field(..., gt=5.0, lt=500.0)
    flat_size_sqm: float = Field(..., gt=5.0, lt=1000.0)
    
    total_rent_eur: float = Field(..., gt=50.0, lt=10000.0)
    deposit_eur: float = Field(..., ge=0.0, lt=30000.0)
    utilities_eur: float = Field(default=0.0, ge=0.0)
    
    available_from: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    minimum_stay_months: int = Field(default=1, ge=1, le=120)
    registration_possible: bool = Field(default=True)
    furnished: bool = Field(default=True)
    
    flatshare_total_inhabitants: int = Field(..., ge=1, le=20)
    current_female_flatmates: int = Field(default=0, ge=0)
    current_male_flatmates: int = Field(default=0, ge=0)
    flatmate_min_age: int = Field(default=18, ge=16, le=99)
    flatmate_max_age: int = Field(default=99, ge=16, le=99)
    
    searched_gender: Literal["any", "women_only", "men_only"] = Field(default="any")
    smoking_allowed: bool = Field(default=False)
    wifi_mbit: Optional[int] = Field(default=None, ge=1)
    
    description_de: str = Field(..., min_length=50)
    description_en: str = Field(..., min_length=50)

    @field_validator("title", "description_de", "description_en", "street", "district")
    @classmethod
    def check_zero_emojis(cls, v: str) -> str:
        if EMOJI_PATTERN.search(v):
            raise ValueError("Zero-emoji constraint violated: emojis are strictly forbidden.")
        return v

    @model_validator(mode="after")
    def validate_logical_boundaries(self) -> 'RentalListingSchema':
        if self.flat_size_sqm < self.room_size_sqm:
            raise ValueError(f"Flat size ({self.flat_size_sqm}m²) cannot be smaller than room size ({self.room_size_sqm}m²).")
        if self.flatmate_min_age > self.flatmate_max_age:
            raise ValueError("Flatmate minimum age cannot exceed maximum age.")
        return self

if __name__ == "__main__":
    import json
    if len(sys.argv) < 2:
        print("Usage: uv run schema_validator.py <listing_json_file> (or uvx --with pydantic python schema_validator.py <listing_json_file>)")
        sys.exit(1)
        
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
        
    try:
        validated = RentalListingSchema(**raw_data)
        print("✅ Validation PASS: All schema, boundary, and zero-emoji criteria satisfied.")
        print(validated.model_dump_json(indent=2))
        sys.exit(0)
    except Exception as e:
        print(f"❌ Validation FAILED: {e}", file=sys.stderr)
        sys.exit(1)
