from datetime import timedelta, date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func
from sqlalchemy.orm import selectinload

from database import get_db
from schemas.movies import MovieListResponseSchema, MovieListItemSchema, UpdateResponse
from database.models import (
    MovieModel,
    CountryModel,
    GenreModel,
    ActorModel,
    LanguageModel
)
from src.schemas.movies import MovieCreate, MovieDetailSchema, MovieUpdate


router = APIRouter()
MOVIES_BASE_PATH = "/theater/movies/"

@router.get("/movies/", response_model=MovieListResponseSchema)
async def list_movies(
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=20),
        db: AsyncSession = Depends(get_db)
):
    offset = (page - 1) * per_page
    result = await db.execute(select(MovieModel).order_by(desc(MovieModel.id)).offset(offset).limit(per_page))
    movies = result.scalars().all()

    if not movies:
        raise HTTPException(status_code=404, detail="No movies found.")

    total_items = await db.scalar(select(func.count(MovieModel.id)))
    total_pages = (total_items + per_page - 1) // per_page

    prev_page = f"{MOVIES_BASE_PATH}?page={page - 1}&per_page={per_page}" if page > 1 else None
    next_page = f"{MOVIES_BASE_PATH}?page={page + 1}&per_page={per_page}" if page < total_pages else None

    return MovieListResponseSchema(
        movies=[MovieListItemSchema.from_orm(m) for m in movies],
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_items
    )


async def get_or_create_country(db: AsyncSession, code: str):
    country = await db.scalar(select(CountryModel).where(CountryModel.code == code))
    if not country:
        country = CountryModel(code=code)
        db.add(country)
        await db.commit()
        await db.refresh(country)
    return country


async def get_or_create_entities(db: AsyncSession, model, names: list):
    entities = []
    for name in names:
        entity = await db.scalar(select(model).where(model.name == name))
        if not entity:
            entity = model(name=name)
            db.add(entity)
            await db.commit()
            await db.refresh(entity)
        entities.append(entity)
    return entities


@router.post("/movies/", response_model=MovieDetailSchema, status_code=201)
async def create_movie(movie: MovieCreate, db: AsyncSession = Depends(get_db)):
    if movie.score < 0 or movie.score > 100:
        raise HTTPException(status_code=400, detail="Score must be between 0 and 100.")
    if movie.budget < 0 or movie.revenue < 0:
        raise HTTPException(status_code=400, detail="Budget and revenue must be non-negative.")
    if movie.date > date.today() + timedelta(days=365):
        raise HTTPException(status_code=400, detail="Date cannot be more than one year in the future.")
    if len(movie.name) > 255:
        raise HTTPException(status_code=400, detail="Name cannot exceed 255 characters.")

    exists = await db.scalar(
        select(MovieModel).where(MovieModel.name == movie.name, MovieModel.date == movie.date)
    )
    if exists:
        raise HTTPException(
            status_code=409,
            detail=f"A movie with the name '{movie.name}' and release date '{movie.date}' already exists."
        )

    country = await get_or_create_country(db, movie.country)
    genres = await get_or_create_entities(db, GenreModel, movie.genres)
    actors = await get_or_create_entities(db, ActorModel, movie.actors)
    languages = await get_or_create_entities(db, LanguageModel, movie.languages)

    new_movie = MovieModel(
        name=movie.name,
        date=movie.date,
        score=movie.score,
        overview=movie.overview,
        status=movie.status,
        budget=movie.budget,
        revenue=movie.revenue,
        country=country,
        genres=genres,
        actors=actors,
        languages=languages
    )
    db.add(new_movie)
    await db.commit()
    await db.refresh(
        new_movie,
        attribute_names=[
            "country",
            "genres",
            "actors",
            "languages"
        ],
        with_for_update=None
    )

    return new_movie


@router.get("/movies/{movie_id}/", response_model=MovieDetailSchema)
async def get_movie_details(movie_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(MovieModel)
        .where(MovieModel.id == movie_id)
        .options(selectinload(MovieModel.country))
        .options(selectinload(MovieModel.genres))
        .options(selectinload(MovieModel.actors))
        .options(selectinload(MovieModel.languages))
    )

    result = await db.execute(stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    return movie


@router.delete("/movies/{movie_id}/", status_code=204)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")
    await db.delete(movie)
    await db.commit()
    return None


@router.patch("/movies/{movie_id}/", response_model=UpdateResponse, status_code=200)
async def update_movie(movie_id: int, update_data: MovieUpdate, db: AsyncSession = Depends(get_db)):
    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    if update_data.score is not None and not (0 <= update_data.score <= 100):
        raise HTTPException(status_code=400, detail="Score must be between 0 and 100.")
    if update_data.budget is not None and update_data.budget < 0:
        raise HTTPException(status_code=400, detail="Budget must be non-negative.")
    if update_data.revenue is not None and update_data.revenue < 0:
        raise HTTPException(status_code=400, detail="Revenue must be non-negative.")
    if update_data.name is not None and len(update_data.name) > 255:
        raise HTTPException(status_code=400, detail="Name cannot exceed 255 characters.")
    if update_data.date is not None and update_data.date > date.today() + timedelta(days=365):
        raise HTTPException(status_code=400, detail="Date cannot be more than one year in the future.")

    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(movie, key, value)

    try:
        await db.commit()
        await db.refresh(movie)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")

    return {"detail": "Movie updated successfully."}
