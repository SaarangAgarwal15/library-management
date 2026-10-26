import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_borrow_and_return_flow():
    with TestClient(app) as c:
        assert c.get("/api/health").json() == {"status": "ok"}
        book = c.post("/api/books", json={"title": "Zzyzx", "author": "A", "isbn": "123", "copies": 1}).json()
        member = c.post("/api/members", json={"name": "N", "email": "n@x.io"}).json()
        loan = c.post("/api/loans", json={"book_id": book["id"], "member_id": member["id"]})
        assert loan.status_code == 201
        assert c.post("/api/loans", json={"book_id": book["id"], "member_id": member["id"]}).status_code == 409
        assert c.post(f"/api/loans/{loan.json()['id']}/return").status_code == 200
        assert c.get("/api/books", params={"q": "zzyzx"}).json()[0]["available"] == 1


def test_duplicate_isbn_rejected():
    with TestClient(app) as c:
        body = {"title": "X", "author": "Y", "isbn": "dup-1", "copies": 1}
        assert c.post("/api/books", json=body).status_code == 201
        assert c.post("/api/books", json=body).status_code == 409
