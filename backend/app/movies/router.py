from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.movies.schemas import (
    MovieCreate,
    MovieDetail,
    MovieListItem,
    MovieUpdate,
    PaginatedMovieList,
    ReviewCreate,
    ReviewCreated,
)
from app.movies.service import create_movie, create_review, delete_movie, get_movie, list_movies, update_movie

movies_router = APIRouter(prefix="/movies", tags=["movies"])
reviews_router = APIRouter(prefix="/reviews", tags=["reviews"])


@movies_router.get("", response_model=PaginatedMovieList)
async def read_movies(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(default=None, min_length=1),
    session: AsyncSession = Depends(get_db),
) -> PaginatedMovieList:
    return await list_movies(session, skip=skip, limit=limit, search=search)


@movies_router.get("/{movie_id}", response_model=MovieDetail)
async def read_movie(movie_id: str, session: AsyncSession = Depends(get_db)) -> MovieDetail:
    return await get_movie(session, movie_id)


@movies_router.post("", response_model=MovieDetail, status_code=status.HTTP_201_CREATED)
async def create_movie_endpoint(
    movie_in: MovieCreate, session: AsyncSession = Depends(get_db)
) -> MovieDetail:
    return await create_movie(session, movie_in)


@movies_router.put("/{movie_id}", response_model=MovieDetail)
async def update_movie_endpoint(
    movie_id: str,
    movie_in: MovieUpdate,
    session: AsyncSession = Depends(get_db),
) -> MovieDetail:
    return await update_movie(session, movie_id, movie_in)


@movies_router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie_endpoint(movie_id: str, session: AsyncSession = Depends(get_db)) -> Response:
    await delete_movie(session, movie_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@reviews_router.post("", response_model=ReviewCreated, status_code=status.HTTP_201_CREATED)
async def create_review_endpoint(
    review_in: ReviewCreate,
    session: AsyncSession = Depends(get_db),
) -> ReviewCreated:
    return await create_review(session, review_in)
