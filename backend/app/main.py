import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, String, create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./library.db")
engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[str] = mapped_column(String(120))
    isbn: Mapped[str] = mapped_column(String(20), unique=True)
    copies: Mapped[int] = mapped_column(default=1)
    available: Mapped[int] = mapped_column(default=1)


class Member(Base):
    __tablename__ = "members"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True)


class Loan(Base):
    __tablename__ = "loans"
    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    borrowed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    due_at: Mapped[datetime] = mapped_column(DateTime)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BookIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=120)
    isbn: str = Field(min_length=3, max_length=20)
    copies: int = Field(default=1, ge=1, le=100)


class MemberIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LoanIn(BaseModel):
    book_id: int
    member_id: int


def get_db():
    with SessionLocal() as db:
        yield db


def seed(db: Session):
    if db.scalar(select(func.count(Book.id))):
        return
    books = [
        ("Middlemarch", "George Eliot", "9780141439549", 3),
        ("The Dispossessed", "Ursula K. Le Guin", "9780061054884", 2),
        ("Invisible Cities", "Italo Calvino", "9780156453806", 2),
        ("Kitchen", "Banana Yoshimoto", "9780802141118", 1),
        ("Things Fall Apart", "Chinua Achebe", "9780385474542", 4),
        ("The Left Hand of Darkness", "Ursula K. Le Guin", "9780441478125", 2),
        ("Pedro Paramo", "Juan Rulfo", "9780802133908", 1),
        ("A Suitable Boy", "Vikram Seth", "9780060786526", 2),
    ]
    db.add_all(Book(title=t, author=a, isbn=i, copies=c, available=c) for t, a, i, c in books)
    db.add_all([Member(name="Asha Verma", email="asha@example.com"),
                Member(name="Rohan Mehta", email="rohan@example.com")])
    db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(title="Library API", lifespan=lifespan)


def book_d(b: Book):
    return {"id": b.id, "title": b.title, "author": b.author, "isbn": b.isbn,
            "copies": b.copies, "available": b.available}


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@app.get("/api/books")
def list_books(q: str = "", db: Session = Depends(get_db)):
    stmt = select(Book).order_by(Book.title)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(Book.title).like(like) | func.lower(Book.author).like(like))
    return [book_d(b) for b in db.scalars(stmt)]


@app.post("/api/books", status_code=201)
def add_book(data: BookIn, db: Session = Depends(get_db)):
    b = Book(**data.model_dump(), available=data.copies)
    db.add(b)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A book with this ISBN already exists")
    return book_d(b)


@app.delete("/api/books/{book_id}", status_code=204)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    b = db.get(Book, book_id)
    if not b:
        raise HTTPException(404, "Book not found")
    if b.available < b.copies:
        raise HTTPException(409, "Copies are still checked out")
    db.query(Loan).filter(Loan.book_id == book_id).delete()
    db.delete(b)
    db.commit()


@app.get("/api/members")
def list_members(db: Session = Depends(get_db)):
    return [{"id": m.id, "name": m.name, "email": m.email}
            for m in db.scalars(select(Member).order_by(Member.name))]


@app.post("/api/members", status_code=201)
def add_member(data: MemberIn, db: Session = Depends(get_db)):
    m = Member(**data.model_dump())
    db.add(m)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A member with this email already exists")
    return {"id": m.id, "name": m.name, "email": m.email}


@app.get("/api/loans")
def list_loans(active: bool = False, db: Session = Depends(get_db)):
    stmt = (select(Loan, Book.title, Member.name)
            .join(Book, Book.id == Loan.book_id).join(Member, Member.id == Loan.member_id)
            .order_by(Loan.borrowed_at.desc()))
    if active:
        stmt = stmt.where(Loan.returned_at.is_(None))
    now = datetime.utcnow()
    return [{"id": ln.id, "book_id": ln.book_id, "book": t, "member": n,
             "borrowed_at": ln.borrowed_at.isoformat(), "due_at": ln.due_at.isoformat(),
             "returned_at": ln.returned_at.isoformat() if ln.returned_at else None,
             "overdue": ln.returned_at is None and ln.due_at < now}
            for ln, t, n in db.execute(stmt)]


@app.post("/api/loans", status_code=201)
def borrow(data: LoanIn, db: Session = Depends(get_db)):
    b, m = db.get(Book, data.book_id), db.get(Member, data.member_id)
    if not b or not m:
        raise HTTPException(404, "Book or member not found")
    if b.available < 1:
        raise HTTPException(409, "No copies available")
    dup = db.scalar(select(Loan).where(Loan.book_id == b.id, Loan.member_id == m.id,
                                       Loan.returned_at.is_(None)))
    if dup:
        raise HTTPException(409, f"{m.name} already has this book")
    b.available -= 1
    loan = Loan(book_id=b.id, member_id=m.id, due_at=datetime.utcnow() + timedelta(days=14))
    db.add(loan)
    db.commit()
    return {"id": loan.id, "due_at": loan.due_at.isoformat()}


@app.post("/api/loans/{loan_id}/return")
def give_back(loan_id: int, db: Session = Depends(get_db)):
    loan = db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(404, "Loan not found")
    if loan.returned_at:
        raise HTTPException(409, "Already returned")
    loan.returned_at = datetime.utcnow()
    db.get(Book, loan.book_id).available += 1
    db.commit()
    return {"id": loan.id, "returned_at": loan.returned_at.isoformat()}


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    active = db.scalar(select(func.count(Loan.id)).where(Loan.returned_at.is_(None)))
    overdue = db.scalar(select(func.count(Loan.id)).where(Loan.returned_at.is_(None), Loan.due_at < now))
    return {"titles": db.scalar(select(func.count(Book.id))),
            "copies": db.scalar(select(func.coalesce(func.sum(Book.copies), 0))),
            "members": db.scalar(select(func.count(Member.id))),
            "on_loan": active, "overdue": overdue}
