"""Carga inicial do catálogo de filmes a partir dos CSVs do bootcamp."""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import delete, insert

from app.db.session import AsyncSessionLocal
from app.movies.models import (
    DimCompany,
    DimGenre,
    DimMovie,
    DimPerson,
    DimReview,
    FactMoviePerformance,
    MovieReview,
    bridge_movie_company,
    bridge_movie_genre,
    bridge_movie_person,
)

LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_ROOT = PROJECT_ROOT / "data" / "raw"


@dataclass(frozen=True)
class CsvTableSpec:
    path: Path
    table: Any


def _clean_value(value: str | None) -> str | None:
    if value is None:
        return None

    stripped = value.strip()
    return stripped or None


def _parse_int(value: str | None) -> int | None:
    cleaned = _clean_value(value)
    if cleaned is None:
        return None
    return int(float(cleaned))


def _parse_float(value: str | None) -> float | None:
    cleaned = _clean_value(value)
    if cleaned is None:
        return None
    return float(cleaned)


def _parse_date(value: str | None) -> date | None:
    cleaned = _clean_value(value)
    if cleaned is None:
        return None
    return date.fromisoformat(cleaned)


def _normalize_row(row: dict[str, str | None]) -> dict[str, Any]:
    return {key: _clean_value(value) for key, value in row.items()}


def _iter_csv_rows(path: Path) -> Iterable[dict[str, str | None]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        yield from reader


def _batchify(rows: Iterable[dict[str, Any]], batch_size: int) -> Iterable[list[dict[str, Any]]]:
    batch: list[dict[str, Any]] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= batch_size:
            yield batch
            batch = []

    if batch:
        yield batch


def _movie_rows(path: Path) -> Iterable[dict[str, Any]]:
    for row in _iter_csv_rows(path):
        normalized = _normalize_row(row)
        yield {
            "sk_movie_id": normalized["sk_movie_id"],
            "id_filme": normalized["id_filme"],
            "titulo": normalized["titulo"],
            "data_lancamento": _parse_date(normalized["data_lancamento"]),
            "ano_lancamento": _parse_int(normalized["ano_lancamento"]),
            "duracao_minutos": _parse_int(normalized["duracao_minutos"]),
            "status_filme": normalized["status_filme"],
            "sinopse": normalized["sinopse"],
            "url_poster": normalized["url_poster"],
            "url_backdrop": normalized["url_backdrop"],
        }


def _genre_rows(path: Path) -> Iterable[dict[str, Any]]:
    for row in _iter_csv_rows(path):
        normalized = _normalize_row(row)
        yield {
            "sk_genre_id": normalized["sk_genre_id"],
            "nome_genero": normalized["nome_genero"],
        }


def _company_rows(path: Path) -> Iterable[dict[str, Any]]:
    for row in _iter_csv_rows(path):
        normalized = _normalize_row(row)
        yield {
            "sk_company_id": normalized["sk_company_id"],
            "nome_produtora": normalized["nome_produtora"],
        }


def _person_rows(path: Path) -> Iterable[dict[str, Any]]:
    for row in _iter_csv_rows(path):
        normalized = _normalize_row(row)
        yield {
            "sk_person_id": normalized["sk_person_id"],
            "nome_pessoa": normalized["nome_pessoa"],
            "tipo_pessoa": normalized["tipo_pessoa"],
        }


def _bridge_rows(path: Path, first_column: str, second_column: str) -> Iterable[dict[str, Any]]:
    for row in _iter_csv_rows(path):
        normalized = _normalize_row(row)
        yield {
            first_column: normalized[first_column],
            second_column: normalized[second_column],
        }


def _performance_rows(path: Path) -> Iterable[dict[str, Any]]:
    for row in _iter_csv_rows(path):
        normalized = _normalize_row(row)
        yield {
            "sk_movie_id": normalized["sk_movie_id"],
            "orcamento_usd": _parse_float(normalized["orcamento_usd"]),
            "receita_usd": _parse_float(normalized["receita_usd"]),
            "lucro_usd": _parse_float(normalized["lucro_usd"]) or 0.0,
            "orcamento_brl": _parse_float(normalized["orcamento_brl"]),
            "receita_brl": _parse_float(normalized["receita_brl"]),
            "lucro_brl": _parse_float(normalized["lucro_brl"]) or 0.0,
            "popularidade": _parse_float(normalized["popularidade"]),
            "nota_tmdb": _parse_float(normalized["nota_tmdb"]),
            "qtd_tmdb": _parse_int(normalized["qtd_tmdb"]),
            "nota_imdb": _parse_float(normalized["nota_imdb"]),
            "qtd_imdb": _parse_int(normalized["qtd_imdb"]),
        }


def _review_summary_rows(path: Path) -> Iterable[dict[str, Any]]:
    for row in _iter_csv_rows(path):
        normalized = _normalize_row(row)
        yield {
            "sk_review_id": normalized["sk_review_id"],
            "sk_movie_id": normalized["sk_movie_id"],
            "qtd_avaliacoes_usuarios": _parse_int(normalized["qtd_avaliacoes_usuarios"]) or 0,
            "nota_media_usuarios": _parse_float(normalized["nota_media_usuarios"]),
        }


def _movie_review_rows(path: Path) -> Iterable[dict[str, Any]]:
    for row in _iter_csv_rows(path):
        normalized = _normalize_row(row)
        yield {
            "sk_movie_review_id": normalized["sk_movie_review_id"],
            "sk_movie_id": normalized["sk_movie_id"],
            "nome": normalized["nome"],
            "nota": _parse_float(normalized["nota"]) or 0.0,
            "comentario": normalized["comentario"],
        }


async def _truncate_tables() -> None:
    tables_in_delete_order = [
        MovieReview.__table__,
        DimReview.__table__,
        FactMoviePerformance.__table__,
        bridge_movie_person,
        bridge_movie_genre,
        bridge_movie_company,
        DimPerson.__table__,
        DimMovie.__table__,
        DimGenre.__table__,
        DimCompany.__table__,
    ]

    async with AsyncSessionLocal() as session:
        for table in tables_in_delete_order:
            await session.execute(delete(table))
        await session.commit()


async def _insert_rows(table: Any, rows: Iterable[dict[str, Any]], batch_size: int) -> int:
    inserted_rows = 0
    async with AsyncSessionLocal() as session:
        async with session.begin():
            for batch in _batchify(rows, batch_size):
                await session.execute(insert(table), batch)
                inserted_rows += len(batch)
    return inserted_rows


async def seed_catalog(data_root: Path, batch_size: int = 5000, reset: bool = True) -> None:
    if reset:
        LOGGER.info("Limpando tabelas antes da carga inicial...")
        await _truncate_tables()

    files = {
        "dim_movies": CsvTableSpec(data_root / "bases-1" / "dim_movies.csv", DimMovie.__table__),
        "dim_genres": CsvTableSpec(data_root / "bases-1" / "dim_genres.csv", DimGenre.__table__),
        "dim_companies": CsvTableSpec(data_root / "bases-1" / "dim_companies.csv", DimCompany.__table__),
        "dim_people": CsvTableSpec(data_root / "bases-1" / "dim_people.csv", DimPerson.__table__),
        "bridge_movie_genre": CsvTableSpec(
            data_root / "bases-2" / "bridge_movie_genre.csv", bridge_movie_genre
        ),
        "bridge_movie_company": CsvTableSpec(
            data_root / "bases-2" / "bridge_movie_company.csv", bridge_movie_company
        ),
        "bridge_movie_person": CsvTableSpec(
            data_root / "bases-2" / "bridge_movie_person.csv", bridge_movie_person
        ),
        "fact_movies_performance": CsvTableSpec(
            data_root / "bases-2" / "fact_movies_performance.csv", FactMoviePerformance.__table__
        ),
        "dim_reviews": CsvTableSpec(data_root / "bases-1" / "dim_reviews.csv", DimReview.__table__),
        "movie_reviews": CsvTableSpec(data_root / "bases-2" / "movies_reviews.csv", MovieReview.__table__),
    }

    row_iterators = {
        "dim_movies": _movie_rows,
        "dim_genres": _genre_rows,
        "dim_companies": _company_rows,
        "dim_people": _person_rows,
        "bridge_movie_genre": lambda path: _bridge_rows(path, "sk_movie_id", "sk_genre_id"),
        "bridge_movie_company": lambda path: _bridge_rows(path, "sk_movie_id", "sk_company_id"),
        "bridge_movie_person": lambda path: _bridge_rows(path, "sk_movie_id", "sk_person_id"),
        "fact_movies_performance": _performance_rows,
        "dim_reviews": _review_summary_rows,
        "movie_reviews": _movie_review_rows,
    }

    load_order = [
        "dim_movies",
        "dim_genres",
        "dim_companies",
        "dim_people",
        "bridge_movie_genre",
        "bridge_movie_company",
        "bridge_movie_person",
        "fact_movies_performance",
        "dim_reviews",
        "movie_reviews",
    ]

    for name in load_order:
        spec = files[name]
        if not spec.path.exists():
            raise FileNotFoundError(f"Arquivo CSV não encontrado: {spec.path}")

        LOGGER.info("Carregando %s a partir de %s", name, spec.path)
        inserted = await _insert_rows(spec.table, row_iterators[name](spec.path), batch_size)
        LOGGER.info("%s carregado com %s linhas", name, inserted)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Carga inicial do catálogo de filmes.")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Diretório base contendo as pastas bases-1 e bases-2.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Quantidade de linhas inseridas por lote.",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Não limpar as tabelas antes de importar os CSVs.",
    )
    return parser


async def _main_async() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if not args.data_root.exists():
        raise FileNotFoundError(f"Diretório de dados não encontrado: {args.data_root}")

    await seed_catalog(args.data_root, batch_size=args.batch_size, reset=not args.no_reset)


def main() -> None:
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()