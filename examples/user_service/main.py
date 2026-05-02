"""
User service example — fastapi-event-bus in action.

Run with:
    uvicorn main:app --reload

Then try:
    POST /users        {"email": "hakan@example.com"}
    DELETE /users/1
"""
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .events import bus  # handlers are registered on import

logging.basicConfig(level=logging.DEBUG)

# In-memory store (demo only)
_users: dict[str, dict] = {}


class CreateUserRequest(BaseModel):
    email: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with bus.lifespan(graceful_timeout=5.0):
        yield


app = FastAPI(title="User Service", lifespan=lifespan)


@app.post("/users", status_code=201)
async def create_user(body: CreateUserRequest) -> dict:
    user_id = str(uuid.uuid4())[:8]
    user = {"id": user_id, "email": body.email}
    _users[user_id] = user

    await bus.emit("user.created", user)

    return user


@app.delete("/users/{user_id}", status_code=200)
async def delete_user(user_id: str) -> dict:
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found")

    user = _users.pop(user_id)
    await bus.emit("user.deleted", user)

    return {"deleted": user_id}


@app.get("/users")
async def list_users() -> list:
    return list(_users.values())