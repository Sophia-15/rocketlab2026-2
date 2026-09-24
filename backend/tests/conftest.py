from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.movies.models import (
    DimCompany,
    DimGenre,
    DimMovie,
    DimPerson,
    DimReview,
    FactMoviePerformance,
    MovieReview,
)


@pytest_asyncio.fixture
async def session_factory(tmp_path) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    yield factory
    await engine.dispose()


async def _seed_movies(session: AsyncSession) -> None:
    sci_fi = DimGenre(sk_genre_id="genre-sci-fi", nome_genero="Science Fiction")
    thriller = DimGenre(sk_genre_id="genre-thriller", nome_genero="Thriller")
    company = DimCompany(sk_company_id="company-1", nome_produtora="Warner Bros")
    director = DimPerson(
        sk_person_id="person-director",
        nome_pessoa="Lana Wachowski",
        tipo_pessoa="Diretor",
    )
    actor = DimPerson(
        sk_person_id="person-actor",
        nome_pessoa="Keanu Reeves",
        tipo_pessoa="Ator",
    )

    matrix = DimMovie(
        sk_movie_id="movie-1",
        id_filme="tt001",
        titulo="Matrix",
        data_lancamento=None,
        ano_lancamento=1999,
        duracao_minutos=136,
        status_filme="Lançado",
        sinopse="A hacker discovers reality is simulated.",
        url_poster="https://example.com/matrix.jpg",
        url_backdrop="https://example.com/matrix-backdrop.jpg",
    )
    matrix.genres = [sci_fi, thriller]
    matrix.companies = [company]
    matrix.people = [director, actor]
    matrix.performance = FactMoviePerformance(
        sk_movie_id="movie-1",
        orcamento_usd=Decimal("63000000"),
        receita_usd=Decimal("466000000"),
        lucro_usd=Decimal("403000000"),
        orcamento_brl=Decimal("315000000"),
        receita_brl=Decimal("2330000000"),
        lucro_brl=Decimal("2015000000"),
        popularidade=99.9,
        nota_tmdb=8.7,
        qtd_tmdb=12000,
        nota_imdb=8.2,
        qtd_imdb=1700000,
    )
    matrix.reviews_summary = DimReview(
        sk_review_id="review-summary-1",
        sk_movie_id="movie-1",
        qtd_avaliacoes_usuarios=2,
        nota_media_usuarios=8.5,
    )
    matrix.reviews = [
        MovieReview(
            sk_movie_review_id="movie-1-review-1",
            sk_movie_id="movie-1",
            nome="Ana",
            nota=9.0,
            comentario="Muito bom.",
        ),
        MovieReview(
            sk_movie_review_id="movie-1-review-2",
            sk_movie_id="movie-1",
            nome="Bruno",
            nota=8.0,
            comentario="Ainda vale a pena rever.",
        ),
    ]

    memento = DimMovie(
        sk_movie_id="movie-2",
        id_filme="tt002",
        titulo="Memento",
        data_lancamento=None,
        ano_lancamento=2000,
        duracao_minutos=113,
        status_filme="Lançado",
        sinopse="A man with short-term memory loss seeks revenge.",
        url_poster="https://example.com/memento.jpg",
        url_backdrop="https://example.com/memento-backdrop.jpg",
    )
    memento.genres = [thriller]

    session.add_all([matrix, memento])
    await session.commit()


@pytest_asyncio.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    async with session_factory() as session:
        await _seed_movies(session)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client

    app.dependency_overrides.clear()
