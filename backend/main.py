"""Campus Customs product API.

This first version is intentionally read-only. It exposes catalogue and
inventory data from the supplied SQLite database without changing it.
"""

from pathlib import Path
import hashlib
import hmac
import json
import secrets
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

try:
    from .agent import AgentDeps, AgentUnavailableError, run_agent
    from .models import ChatHistoryResponse, ChatRequest, ChatResponse, ConversationMessage, CustomerContext, ProductSearchCard, VerifiedPageContext
    from .tools import lookup_product
    from .audit import record_activity
except ImportError:  # Supports `uvicorn main:app` from the backend directory.
    from agent import AgentDeps, AgentUnavailableError, run_agent
    from models import ChatHistoryResponse, ChatRequest, ChatResponse, ConversationMessage, CustomerContext, ProductSearchCard, VerifiedPageContext
    from tools import lookup_product
    from audit import record_activity


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "campus_customs.db"
DATA_PATH = PROJECT_ROOT / "data"
PBKDF2_ITERATIONS = 120_000
SESSION_COOKIE = "campus_customs_session"
sessions: Dict[str, int] = {}

app = FastAPI(title="Campus Customs API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.mount("/images", StaticFiles(directory=DATA_PATH), name="images")


@app.on_event("startup")
def audit_backend_start() -> None:
    record_activity("backend.startup", {}, {"status": "started"}, "backend startup completed")


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def product_image_url(image_file_path: str) -> str:
    return "/images/" + image_file_path.lstrip("/")


def product_from_row(row: sqlite3.Row) -> Dict[str, Any]:
    product = dict(row)
    product["image_url"] = product_image_url(product.pop("image_file_path"))
    return product


class RegistrationRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    ).hex()
    return "pbkdf2_sha256${}${}".format(salt, digest)


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, expected_digest = stored_hash.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    actual_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    ).hex()
    return hmac.compare_digest(actual_digest, expected_digest)


def public_user(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "email": row["email"],
    }


def set_session(response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    sessions[token] = user_id
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 7,
    )


def authenticated_user(session: Optional[str]) -> Optional[Dict[str, Any]]:
    if not session or session not in sessions:
        return None
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, first_name, last_name, email FROM users WHERE id = ?",
            (sessions[session],),
        ).fetchone()
    return public_user(row) if row else None


def load_chat_history(user_id: int) -> List[ConversationMessage]:
    with get_connection() as connection:
        rows = connection.execute(
            """SELECT role, content, products_json, created_at FROM chat_messages
               WHERE user_id = ? ORDER BY id DESC LIMIT 20""",
            (user_id,),
        ).fetchall()
    messages: List[ConversationMessage] = []
    for row in reversed(rows):
        products: List[ProductSearchCard] = []
        if row["products_json"]:
            try:
                products = [ProductSearchCard(**item) for item in json.loads(row["products_json"])]
            except (TypeError, ValueError):
                products = []
        messages.append(ConversationMessage(role=row["role"], content=row["content"], created_at=row["created_at"], products=products))
    return messages


def save_chat_message(user_id: int, role: str, content: str, products: List[ProductSearchCard]) -> None:
    serialized_products = json.dumps([product.model_dump() for product in products]) if products else None
    with get_connection() as connection:
        connection.execute(
            """INSERT INTO chat_messages (user_id, role, content, products_json)
               VALUES (?, ?, ?, ?)""",
            (user_id, role, content, serialized_products),
        )
        connection.commit()


def verified_page_context(product_id: Optional[str]) -> Optional[VerifiedPageContext]:
    if not product_id:
        return None
    product = lookup_product(product_id)
    if not product.found or not product.product_id or product.name is None or product.description is None or product.price is None or product.colors is None:
        return None
    return VerifiedPageContext(
        product_id=product.product_id,
        name=product.name,
        description=product.description,
        price=product.price,
        colors=product.colors,
        sizes=product.sizes,
    )


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, campus_customs_session: Optional[str] = Cookie(default=None)) -> ChatResponse:
    user_record = authenticated_user(campus_customs_session)
    history = load_chat_history(user_record["id"]) if user_record else []
    deps = AgentDeps(
        customer=CustomerContext(**user_record) if user_record else None,
        page=verified_page_context(payload.page_context.product_id if payload.page_context else None),
        history=history,
    )
    if user_record:
        save_chat_message(user_record["id"], "user", payload.message.strip(), [])
    try:
        reply, products = await run_agent(payload.message.strip(), deps=deps)
    except AgentUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except Exception:
        raise HTTPException(status_code=502, detail="The chat service is temporarily unavailable.")
    if user_record:
        save_chat_message(user_record["id"], "assistant", reply, products)
    return ChatResponse(reply=reply, products=products)


@app.get("/api/chat/history", response_model=ChatHistoryResponse)
def chat_history(campus_customs_session: Optional[str] = Cookie(default=None)) -> ChatHistoryResponse:
    user_record = authenticated_user(campus_customs_session)
    if not user_record:
        raise HTTPException(status_code=401, detail="Log in to retrieve chat history.")
    return ChatHistoryResponse(messages=load_chat_history(user_record["id"]))


@app.get("/api/products")
def list_products() -> List[Dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """SELECT product_id, name, garment_type, description, colors,
                      search_tags, image_file_path, price
               FROM catalogue ORDER BY name"""
        ).fetchall()
    return [product_from_row(row) for row in rows]


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> Dict[str, Any]:
    with get_connection() as connection:
        product_row = connection.execute(
            """SELECT product_id, name, garment_type, description, colors,
                      search_tags, image_file_path, price
               FROM catalogue WHERE product_id = ?""",
            (product_id,),
        ).fetchone()
        if product_row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        inventory_rows = connection.execute(
            """SELECT size, quantity FROM inventory
               WHERE product_id = ? ORDER BY size""",
            (product_id,),
        ).fetchall()

    product = product_from_row(product_row)
    product["inventory"] = [dict(row) for row in inventory_rows]
    return product


@app.post("/api/auth/register", status_code=201)
def register(payload: RegistrationRequest, response: Response) -> Dict[str, Any]:
    first_name = payload.first_name.strip()
    last_name = payload.last_name.strip()
    email = str(payload.email).lower()
    if not first_name or not last_name:
        raise HTTPException(status_code=422, detail="First and last name are required.")
    password_hash = hash_password(payload.password)
    with get_connection() as connection:
        try:
            cursor = connection.execute(
                """INSERT INTO users (name, email, password_hash, first_name, last_name)
                   VALUES (?, ?, ?, ?, ?)""",
                ("{} {}".format(first_name, last_name), email, password_hash, first_name, last_name),
            )
            user_id = cursor.lastrowid
            row = connection.execute(
                "SELECT id, first_name, last_name, email FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            connection.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="An account with that email already exists.")
    set_session(response, user_id)
    return {"user": public_user(row), "message": "Your account was created successfully."}


@app.post("/api/auth/login")
def login(payload: LoginRequest, response: Response) -> Dict[str, Any]:
    email = str(payload.email).lower()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, first_name, last_name, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    if row is None or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    set_session(response, row["id"])
    return {"user": public_user(row), "message": "You are now logged in."}


@app.get("/api/auth/me")
def me(campus_customs_session: Optional[str] = Cookie(default=None)) -> Dict[str, Any]:
    user = authenticated_user(campus_customs_session)
    return {"user": user}


@app.post("/api/auth/logout")
def logout(response: Response, campus_customs_session: Optional[str] = Cookie(default=None)) -> Dict[str, str]:
    if campus_customs_session:
        sessions.pop(campus_customs_session, None)
    response.delete_cookie(SESSION_COOKIE)
    return {"message": "You have been logged out."}
