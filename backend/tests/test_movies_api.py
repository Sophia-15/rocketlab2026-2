import pytest


@pytest.mark.asyncio
async def test_list_movies_supports_pagination_and_search(client) -> None:
    response = await client.get("/api/v1/movies", params={"skip": 0, "limit": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["limit"] == 1
    assert payload["skip"] == 0
    assert payload["has_more"] is True
    assert len(payload["items"]) == 1

    response = await client.get("/api/v1/movies", params={"search": "Memento"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["titulo"] == "Memento"


@pytest.mark.asyncio
async def test_movie_detail_includes_reviews_and_summary(client) -> None:
    response = await client.get("/api/v1/movies/movie-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["titulo"] == "Matrix"
    assert payload["review_count"] == 2
    assert payload["average_rating"] == 8.5
    assert len(payload["genres"]) == 2
    assert len(payload["companies"]) == 1
    assert len(payload["people"]) == 2
    assert len(payload["reviews"]) == 2


@pytest.mark.asyncio
async def test_create_review_updates_summary(client) -> None:
    response = await client.post(
        "/api/v1/reviews",
        json={
            "movie_id": "movie-2",
            "nome": "Carla",
            "nota": 9.5,
            "comentario": "Excelente suspense.",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["nome"] == "Carla"
    assert payload["nota"] == 9.5

    response = await client.get("/api/v1/movies/movie-2")
    assert response.status_code == 200
    payload = response.json()
    assert payload["review_count"] == 1
    assert payload["average_rating"] == 9.5
    assert len(payload["reviews"]) == 1


@pytest.mark.asyncio
async def test_movie_crud_flow(client) -> None:
    create_response = await client.post(
        "/api/v1/movies",
        json={
            "id_filme": "tt999",
            "titulo": "New Movie",
            "data_lancamento": "2026-09-24",
            "ano_lancamento": 2026,
            "duracao_minutos": 120,
            "status_filme": "Rascunho",
            "sinopse": "Uma nova produção.",
            "url_poster": "https://example.com/new.jpg",
            "url_backdrop": "https://example.com/new-backdrop.jpg",
        },
    )

    assert create_response.status_code == 201
    created_movie = create_response.json()
    movie_id = created_movie["sk_movie_id"]
    assert created_movie["titulo"] == "New Movie"

    update_response = await client.put(
        f"/api/v1/movies/{movie_id}",
        json={"titulo": "Updated Movie", "status_filme": "Lançado"},
    )

    assert update_response.status_code == 200
    updated_movie = update_response.json()
    assert updated_movie["titulo"] == "Updated Movie"
    assert updated_movie["status_filme"] == "Lançado"

    delete_response = await client.delete(f"/api/v1/movies/{movie_id}")
    assert delete_response.status_code == 204

    not_found_response = await client.get(f"/api/v1/movies/{movie_id}")
    assert not_found_response.status_code == 404
