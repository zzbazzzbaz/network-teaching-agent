from __future__ import annotations

import io
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.models.user import Users
from tests.conftest import INTERNAL_TOKEN

FILES = "/api/v1/files"


def _login(
    client: TestClient,
    username: str = "alice",
    password: str = "password123",
) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _image_bytes(
    image_format: str = "PNG",
    *,
    size: tuple[int, int] = (40, 30),
    color: tuple[int, int, int] = (32, 128, 200),
    orientation: int | None = None,
) -> bytes:
    image = Image.new("RGB", size, color)
    output = io.BytesIO()
    kwargs: dict[str, object] = {}
    if orientation is not None:
        exif = Image.Exif()
        exif[274] = orientation
        kwargs["exif"] = exif
    image.save(output, format=image_format, **kwargs)
    return output.getvalue()


def _upload(
    client: TestClient,
    headers: dict[str, str],
    data: bytes,
    *,
    filename: str = "题目.png",
    content_type: str = "image/png",
) -> dict[str, Any]:
    response = client.post(
        FILES,
        headers=headers,
        files={"file": (filename, data, content_type)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_and_read_image(client: TestClient, create_user: Callable[..., Users]) -> None:
    create_user()
    headers = _login(client)
    data = _image_bytes("PNG")

    uploaded = _upload(client, headers, data)
    assert uploaded["name"] == "题目.png"
    assert uploaded["mime"] == "image/png"
    assert uploaded["size_bytes"] > 0
    file_id = uploaded["file_id"]

    raw = client.get(f"{FILES}/{file_id}/raw", headers=headers)
    assert raw.status_code == 200
    assert raw.headers["content-type"] == "image/png"
    assert "filename*=UTF-8''" in raw.headers["content-disposition"]
    assert raw.content.startswith(b"\x89PNG")

    thumb = client.get(f"{FILES}/{file_id}/thumb", headers=headers)
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/webp"
    with Image.open(io.BytesIO(thumb.content)) as image:
        assert max(image.size) <= 320


def test_transparent_png_is_flattened_to_white(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login(client)
    image = Image.new("RGBA", (20, 20), (255, 0, 0, 0))
    output = io.BytesIO()
    image.save(output, format="PNG")

    uploaded = _upload(client, headers, output.getvalue())
    raw = client.get(f"{FILES}/{uploaded['file_id']}/raw", headers=headers)
    assert raw.status_code == 200
    with Image.open(io.BytesIO(raw.content)) as normalized:
        assert normalized.convert("RGB").getpixel((0, 0)) == (255, 255, 255)


@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WEBP"])
def test_upload_supports_three_formats(
    client: TestClient,
    create_user: Callable[..., Users],
    image_format: str,
) -> None:
    create_user()
    headers = _login(client)
    mime = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
    }[image_format]

    uploaded = _upload(
        client,
        headers,
        _image_bytes(image_format),
        filename=f"image.{image_format.lower()}",
        content_type=mime,
    )
    raw = client.get(f"{FILES}/{uploaded['file_id']}/raw", headers=headers)
    assert raw.status_code == 200
    assert raw.headers["content-type"] == mime


def test_upload_exif_orientation_is_normalized(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login(client)
    uploaded = _upload(
        client,
        headers,
        _image_bytes("JPEG", size=(80, 40), orientation=6),
        filename="photo.jpg",
        content_type="image/jpeg",
    )

    raw = client.get(f"{FILES}/{uploaded['file_id']}/raw", headers=headers)
    assert raw.status_code == 200
    with Image.open(io.BytesIO(raw.content)) as image:
        assert image.size == (40, 80)


def test_upload_rejects_non_image(client: TestClient, create_user: Callable[..., Users]) -> None:
    create_user()
    headers = _login(client)

    response = client.post(
        FILES,
        headers=headers,
        files={"file": ("fake.png", b"%PDF-1.7\n", "image/png")},
    )
    assert response.status_code == 415

    svg = client.post(
        FILES,
        headers=headers,
        files={"file": ("x.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>", "image/svg+xml")},
    )
    assert svg.status_code == 415

    gif = client.post(
        FILES,
        headers=headers,
        files={"file": ("x.gif", b"GIF89a", "image/gif")},
    )
    assert gif.status_code == 415


def test_upload_rejects_oversized_file(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login(client)

    response = client.post(
        FILES,
        headers=headers,
        files={"file": ("big.png", b"\x00" * (10 * 1024 * 1024 + 1), "image/png")},
    )
    assert response.status_code == 413


def test_upload_rejects_too_many_pixels(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login(client)

    response = client.post(
        FILES,
        headers=headers,
        files={"file": ("wide.png", _image_bytes("PNG", size=(9000, 1)), "image/png")},
    )
    assert response.status_code == 422


def test_upload_requires_file(client: TestClient, create_user: Callable[..., Users]) -> None:
    create_user()
    headers = _login(client)

    response = client.post(FILES, headers=headers)
    assert response.status_code == 400

    empty = client.post(
        FILES,
        headers=headers,
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert empty.status_code == 400


def test_file_ownership_isolation(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user("alice", "password123")
    create_user("bob", "password456")
    alice = _login(client, "alice", "password123")
    bob = _login(client, "bob", "password456")

    uploaded = _upload(client, alice, _image_bytes("PNG"))
    file_id = uploaded["file_id"]

    assert client.get(f"{FILES}/{file_id}/raw", headers=bob).status_code == 404
    assert client.get(f"{FILES}/{file_id}/thumb", headers=bob).status_code == 404
    assert client.delete(f"{FILES}/{file_id}", headers=bob).status_code == 404
    assert client.get(f"{FILES}/{file_id}/raw", headers=alice).status_code == 200


def test_delete_is_idempotent(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login(client)
    uploaded = _upload(client, headers, _image_bytes("PNG"))
    file_id = uploaded["file_id"]

    assert client.delete(f"{FILES}/{file_id}", headers=headers).status_code == 204
    assert client.delete(f"{FILES}/{file_id}", headers=headers).status_code == 204
    assert client.get(f"{FILES}/{file_id}/raw", headers=headers).status_code == 404
    assert client.get(f"{FILES}/{file_id}/thumb", headers=headers).status_code == 404


def test_internal_file_endpoints(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    headers = _login(client)
    uploaded = _upload(client, headers, _image_bytes("PNG"))
    file_id = uploaded["file_id"]
    internal = {
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-User-Id": str(user.user_id),
    }

    metadata = client.get(f"/internal/files/{file_id}", headers=internal)
    assert metadata.status_code == 200
    assert metadata.json() == {
        "file_id": file_id,
        "name": "题目.png",
        "mime": "image/png",
        "size_bytes": uploaded["size_bytes"],
    }

    raw = client.get(f"/internal/files/{file_id}/raw", headers=internal)
    assert raw.status_code == 200
    assert raw.headers["content-type"] == "image/png"

    assert client.get(f"/internal/files/{file_id}").status_code == 401
    wrong = {**internal, "X-Internal-Token": "wrong"}
    assert client.get(f"/internal/files/{file_id}", headers=wrong).status_code == 403

    other = {**internal, "X-User-Id": str(uuid.uuid4())}
    assert client.get(f"/internal/files/{file_id}", headers=other).status_code == 404
