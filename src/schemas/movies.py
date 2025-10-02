from datetime import date, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum


class StatusEnum(str, Enum):
    released = "Released"
    post_production = "Post Production"
    in_production = "In Production"


class EntityOut(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True
        from_attributes = True


class CountryOut(BaseModel):
    id: int
    code: str
    name: Optional[str]

    class Config:
        orm_mode = True
        from_attributes = True

    @validator("code")
    def validate_code(cls, v):
        if len(v) not in (2, 3):
            raise ValueError("Invalid country code")
        return v


class MovieBase(BaseModel):
    name: str = Field(..., max_length=255)
    date: date
    score: float = Field(..., ge=0, le=100)
    overview: str
    status: StatusEnum
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)
    country: str = Field(..., min_length=2, max_length=3)
    genres: List[str]
    actors: List[str]
    languages: List[str]

    @validator("date")
    def validate_date(cls, v):
        if v > date.today() + timedelta(days=365):
            raise ValueError("Invalid date")
        return v


class MovieCreate(MovieBase):
    pass


class MovieUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    date: Optional[date] = None
    score: Optional[float] = Field(None, ge=0, le=100)
    overview: Optional[str] = None
    status: Optional[StatusEnum] = None
    budget: Optional[float] = Field(None, ge=0)
    revenue: Optional[float] = Field(None, ge=0)
    country: Optional[str] = Field(None, min_length=2, max_length=3)
    genres: Optional[List[str]] = None
    actors: Optional[List[str]] = None
    languages: Optional[List[str]] = None

    @validator("date")
    def validate_date(cls, v):
        if v and v > date.today() + timedelta(days=365):
            raise ValueError("Invalid date")
        return v


class MovieDetailSchema(MovieBase):
    id: int
    country: CountryOut
    genres: List[EntityOut]
    actors: List[EntityOut]
    languages: List[EntityOut]

    class Config:
        orm_mode = True
        from_attributes = True


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    date: date
    score: float
    overview: str

    class Config:
        orm_mode = True
        from_attributes = True


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    total_items: int
    total_pages: int
    prev_page: Optional[str]
    next_page: Optional[str]


class UpdateResponse(BaseModel):
    detail: str
