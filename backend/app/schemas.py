from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Literal

from .catalog import INTERESTS

class ChatTurn(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=1500)

    @field_validator("role")
    @classmethod
    def valid_role(cls, v):
        if v not in ("user", "assistant"):
            raise ValueError("role must be user or assistant")
        return v

class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=1200)

    @field_validator('message')
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError('Please enter a question with at least two visible characters')
        return value.strip()
    language: str = Field(default="English", pattern="^(English|Arabic|French)$")
    history: list[ChatTurn] = Field(default_factory=list, max_length=8)

class PlanRequest(BaseModel):
    cities: list[str] = Field(min_length=1, max_length=8)
    days: int = Field(ge=1, le=30)
    interests: list[str] = Field(default_factory=lambda: ["history", "culture"], max_length=8)
    pace: str = Field(default="balanced", pattern="^(relaxed|balanced|packed)$")
    family: bool = False
    optimize_route: bool = False
    language: str = Field(default="en", pattern="^(en|ar)$")
    budget_usd: int | None = Field(default=None, ge=1, le=1000000)
    traveler_profile: dict | None = None

    @field_validator('traveler_profile')
    @classmethod
    def valid_profile(cls, value):
        return TravelerProfile.model_validate(value).model_dump() if value is not None else None

    @field_validator("cities")
    @classmethod
    def cities_not_empty(cls, v):
        names = list(dict.fromkeys(x.strip() for x in v if x.strip()))
        if not names: raise ValueError("Select at least one city")
        return names

    @field_validator("interests")
    @classmethod
    def interests_valid(cls, v):
        for interest in v:
            if interest not in INTERESTS:
                raise ValueError(f"Unknown interest: {interest}")
        return list(dict.fromkeys(v))


class TripPhase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = Field(pattern="^(history|beach|mixed)$")
    days: int = Field(ge=1, le=30)
    cities: list[str] = Field(min_length=1, max_length=5)
    interests: list[str] = Field(default_factory=list, max_length=8)


class DayOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_stops: Literal[0, 1]
    family_friendly: bool = False

    @field_validator('max_stops', mode='before')
    @classmethod
    def strict_stop_count(cls, value):
        if type(value) is not int:
            raise ValueError('Stop count must be an integer')
        return value


class TravelerProfile(BaseModel):
    model_config = ConfigDict(extra='forbid')
    adults: int | None = Field(default=None, ge=1, le=20, strict=True)
    children_ages: list[int] = Field(default_factory=list, max_length=12)
    food_preferences: list[Literal['vegetarian', 'vegan', 'halal']] = Field(default_factory=list, max_length=3)

    @field_validator('children_ages', mode='before')
    @classmethod
    def valid_ages(cls, ages):
        if not isinstance(ages, list) or any(type(age) is not int or not 0 <= age <= 17 for age in ages):
            raise ValueError('Children ages must be whole years between 0 and 17')
        return ages


class TripState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    days: int = Field(ge=1, le=30)
    budget_egp: int | None = Field(default=None, ge=1, le=100000000)
    budget_usd: int | None = Field(default=None, ge=1, le=1000000)
    phases: list[TripPhase] = Field(min_length=1, max_length=5)
    pace: str = Field(default="balanced", pattern="^(relaxed|balanced|packed)$")
    family: bool = False
    traveler_profile: TravelerProfile = Field(default_factory=TravelerProfile)
    accessibility_needs: bool = False
    lighter_cities: list[str] = Field(default_factory=list, max_length=5)
    day_overrides: dict[int, DayOverride] = Field(default_factory=dict)
    required_place_ids: list[Literal['giza-pyramids', 'grand-egyptian-museum']] = Field(default_factory=list, max_length=2)
    swimming_days: int = Field(default=0, ge=0, le=30, strict=True)

    @model_validator(mode='after')
    def validate_trip_invariants(self):
        if sum(phase.days for phase in self.phases) != self.days:
            raise ValueError('Phase days must equal total trip days')
        if self.swimming_days > sum(p.days for p in self.phases if p.kind == 'beach'):
            raise ValueError('Swimming days must fit the coastal allocation')
        for phase in self.phases:
            if phase.days < len(phase.cities):
                raise ValueError('Each planned city needs at least one day')
            if len(set(phase.cities)) != len(phase.cities):
                raise ValueError('Duplicate city in itinerary phase')
        planned_cities = {city for phase in self.phases for city in phase.cities}
        if self.required_place_ids and 'Giza' not in planned_cities:
            raise ValueError('Requested Giza attractions need Giza in the route')
        if len(set(self.required_place_ids)) != len(self.required_place_ids):
            raise ValueError('Requested attractions must be unique')
        if len(set(self.lighter_cities)) != len(self.lighter_cities) or not set(self.lighter_cities) <= planned_cities:
            raise ValueError('Lighter days must name distinct planned cities')
        if len(self.day_overrides) > 30 or any(day < 1 or day > self.days for day in self.day_overrides):
            raise ValueError('Day edits must target an existing trip day')
        return self


class ConsultRequest(ChatRequest):
    trip_state: TripState | None = None
