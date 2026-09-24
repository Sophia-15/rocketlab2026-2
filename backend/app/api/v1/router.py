from fastapi import APIRouter

from app.movies.router import movies_router, reviews_router

api_router = APIRouter()

api_router.include_router(movies_router)
api_router.include_router(reviews_router)
