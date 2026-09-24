from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.movies.models import DimCompany, DimMovie, DimPerson, DimReview, MovieReview
from app.movies.schemas import (
    CompanySummary,
    MovieCreate,
    MovieDetail,
    MovieListItem,
    MovieReviewRead,
    MovieUpdate,
    PaginatedMovieList,
    PerformanceSummary,
    PersonSummary,
    ReviewCreate,
    ReviewCreated,
    ReviewSummary,
    GenreSummary,
)


def _coalesce_decimal(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _build_average(movie: DimMovie) -> float | None:
    if movie.reviews_summary and movie.reviews_summary.nota_media_usuarios is not None:
        return movie.reviews_summary.nota_media_usuarios

    if not movie.reviews:
        return None

    total = sum(review.nota for review in movie.reviews)
    return round(total / len(movie.reviews), 2)


def _build_review_count(movie: DimMovie) -> int:
    if movie.reviews_summary:
        return movie.reviews_summary.qtd_avaliacoes_usuarios
    return len(movie.reviews)


def _movie_list_item(movie: DimMovie) -> MovieListItem:
    return MovieListItem(
        sk_movie_id=movie.sk_movie_id,
        id_filme=movie.id_filme,
        titulo=movie.titulo,
        data_lancamento=movie.data_lancamento,
        ano_lancamento=movie.ano_lancamento,
        duracao_minutos=movie.duracao_minutos,
        status_filme=movie.status_filme,
        sinopse=movie.sinopse,
        url_poster=movie.url_poster,
        url_backdrop=movie.url_backdrop,
        genres=[GenreSummary.model_validate(genre) for genre in movie.genres],
        average_rating=_build_average(movie),
        review_count=_build_review_count(movie),
    )


def _movie_detail(movie: DimMovie) -> MovieDetail:
    performance = None
    if movie.performance is not None:
        performance = PerformanceSummary(
            sk_movie_id=movie.performance.sk_movie_id,
            orcamento_usd=_coalesce_decimal(movie.performance.orcamento_usd),
            receita_usd=_coalesce_decimal(movie.performance.receita_usd),
            lucro_usd=_coalesce_decimal(movie.performance.lucro_usd),
            orcamento_brl=_coalesce_decimal(movie.performance.orcamento_brl),
            receita_brl=_coalesce_decimal(movie.performance.receita_brl),
            lucro_brl=_coalesce_decimal(movie.performance.lucro_brl),
            popularidade=movie.performance.popularidade,
            nota_tmdb=movie.performance.nota_tmdb,
            qtd_tmdb=movie.performance.qtd_tmdb,
            nota_imdb=movie.performance.nota_imdb,
            qtd_imdb=movie.performance.qtd_imdb,
        )

    reviews_summary = None
    if movie.reviews_summary is not None:
        reviews_summary = ReviewSummary.model_validate(movie.reviews_summary)

    return MovieDetail(
        sk_movie_id=movie.sk_movie_id,
        id_filme=movie.id_filme,
        titulo=movie.titulo,
        data_lancamento=movie.data_lancamento,
        ano_lancamento=movie.ano_lancamento,
        duracao_minutos=movie.duracao_minutos,
        status_filme=movie.status_filme,
        sinopse=movie.sinopse,
        url_poster=movie.url_poster,
        url_backdrop=movie.url_backdrop,
        genres=[GenreSummary.model_validate(genre) for genre in movie.genres],
        average_rating=_build_average(movie),
        review_count=_build_review_count(movie),
        companies=[CompanySummary.model_validate(company) for company in movie.companies],
        people=[PersonSummary.model_validate(person) for person in movie.people],
        performance=performance,
        reviews_summary=reviews_summary,
        reviews=[MovieReviewRead.model_validate(review) for review in movie.reviews],
    )


async def _load_movie_detail(session: AsyncSession, movie_id: str) -> DimMovie:
    statement = (
        select(DimMovie)
        .where(DimMovie.sk_movie_id == movie_id)
        .options(
            selectinload(DimMovie.genres),
            selectinload(DimMovie.companies),
            selectinload(DimMovie.people),
            selectinload(DimMovie.performance),
            selectinload(DimMovie.reviews_summary),
            selectinload(DimMovie.reviews),
        )
    )
    result = await session.execute(statement)
    movie = result.scalar_one_or_none()
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return movie


async def list_movies(
    session: AsyncSession,
    *,
    skip: int,
    limit: int,
    search: str | None = None,
) -> PaginatedMovieList:
    filters = []
    normalized_search = search.strip() if search else None
    if normalized_search:
        pattern = f"%{normalized_search}%"
        filters.append(
            or_(
                DimMovie.titulo.ilike(pattern),
                DimMovie.sinopse.ilike(pattern),
                DimMovie.id_filme.ilike(pattern),
            )
        )

    count_statement = select(func.count(DimMovie.sk_movie_id))
    if filters:
        count_statement = count_statement.where(*filters)

    total = await session.scalar(count_statement)
    total = total or 0

    statement = (
        select(DimMovie)
        .options(
            selectinload(DimMovie.genres),
            selectinload(DimMovie.reviews_summary),
            selectinload(DimMovie.reviews),
        )
        .order_by(DimMovie.titulo)
        .offset(skip)
        .limit(limit)
    )
    if filters:
        statement = statement.where(*filters)

    result = await session.execute(statement)
    movies = result.scalars().unique().all()

    items = [_movie_list_item(movie) for movie in movies]
    return PaginatedMovieList(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=skip + len(items) < total,
    )


async def get_movie(session: AsyncSession, movie_id: str) -> MovieDetail:
    movie = await _load_movie_detail(session, movie_id)
    return _movie_detail(movie)


async def create_movie(session: AsyncSession, movie_in: MovieCreate) -> MovieDetail:
    movie = DimMovie(
        id_filme=movie_in.id_filme,
        titulo=movie_in.titulo,
        data_lancamento=movie_in.data_lancamento,
        ano_lancamento=movie_in.ano_lancamento,
        duracao_minutos=movie_in.duracao_minutos,
        status_filme=movie_in.status_filme,
        sinopse=movie_in.sinopse,
        url_poster=movie_in.url_poster,
        url_backdrop=movie_in.url_backdrop,
    )
    session.add(movie)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie identifier already exists",
        ) from exc

    return await get_movie(session, movie.sk_movie_id)


async def update_movie(session: AsyncSession, movie_id: str, movie_in: MovieUpdate) -> MovieDetail:
    movie = await _load_movie_detail(session, movie_id)
    update_data = movie_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(movie, field, value)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie identifier already exists",
        ) from exc

    return await get_movie(session, movie_id)


async def delete_movie(session: AsyncSession, movie_id: str) -> None:
    movie = await _load_movie_detail(session, movie_id)
    await session.delete(movie)
    await session.commit()


async def create_review(session: AsyncSession, review_in: ReviewCreate) -> ReviewCreated:
    movie = await _load_movie_detail(session, review_in.movie_id)

    review = MovieReview(
        sk_movie_id=movie.sk_movie_id,
        nome=review_in.nome,
        nota=review_in.nota,
        comentario=review_in.comentario,
    )
    session.add(review)
    await session.flush()
    await session.refresh(review)

    aggregate_statement = select(
        func.count(MovieReview.sk_movie_review_id),
        func.avg(MovieReview.nota),
    ).where(MovieReview.sk_movie_id == movie.sk_movie_id)
    aggregate_result = await session.execute(aggregate_statement)
    total_reviews, average_rating = aggregate_result.one()

    review_summary = movie.reviews_summary
    if review_summary is None:
        review_summary = DimReview(
            sk_movie_id=movie.sk_movie_id,
            qtd_avaliacoes_usuarios=int(total_reviews),
            nota_media_usuarios=float(round(average_rating or 0, 2)),
        )
        session.add(review_summary)
    else:
        review_summary.qtd_avaliacoes_usuarios = int(total_reviews)
        review_summary.nota_media_usuarios = float(round(average_rating or 0, 2))

    await session.commit()

    return ReviewCreated.model_validate(review)
