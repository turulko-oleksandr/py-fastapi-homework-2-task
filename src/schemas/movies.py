from pydantic import BaseModel
from typing import List, Optional
from datetime import date


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
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int

    class Config:
        orm_mode = True
        from_attributes = True


class MovieCreate(BaseModel):
    name: str
    date: date
    score: float
    overview: str
    status: str
    budget: float
    revenue: float
    country: str
    genres: List[str]
    actors: List[str]
    languages: List[str]


class CountryOut(BaseModel):
    id: int
    code: str
    name: Optional[str]

    class Config:
        orm_mode = True
        from_attributes = True


class EntityOut(BaseModel):
    id: int
    name: str


class MovieDetailSchema(BaseModel):
    id: int
    name: str
    date: date
    score: float
    overview: str
    status: str
    budget: float
    revenue: float
    country: CountryOut
    genres: List[EntityOut]
    actors: List[EntityOut]
    languages: List[EntityOut]


class MovieUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[date] = None
    score: Optional[float] = None
    overview: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[float] = None
    revenue: Optional[float] = None

    class Config:
        orm_mode = True


class UpdateResponse(BaseModel):
    detail: str
