import sqlite3
import shutil
import uuid
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi import APIRouter, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Правильный контекстный менеджер для гарантированного закрытия соединения с БД
@contextmanager
def get_db_connection():
    conn = sqlite3.connect("places.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# Функция для инициализации базы данных при старте
@app.on_event("startup")
def startup_event():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Таблица мест
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                contact_info TEXT,
                description TEXT,
                category TEXT,
                latitude REAL,
                longitude REAL
            )
        """)
        
        # Таблица отзывов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                place_id INTEGER NOT NULL,
                author TEXT NOT NULL,
                rating INTEGER NOT NULL,
                text TEXT NOT NULL,
                FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE
            )
        """)
        
        # Таблица пользователей (профили)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                university TEXT NOT NULL,
                faculty TEXT NOT NULL,
                bio TEXT
            )
        """)

        # Таблица групп / сообществ
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                creator_id INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                sender_telegram_id INTEGER NOT NULL,
                sender_name TEXT NOT NULL,
                text TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            )
        """)

# Pydantic-модели с валидацией
class PlaceCreate(BaseModel):
    name: str
    address: str
    contact_info: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ReviewCreate(BaseModel):
    author: str
    rating: int = Field(..., ge=1, le=5, description="Рейтинг должен быть от 1 до 5")
    text: str

class UserProfileCreate(BaseModel):
    telegram_id: int
    first_name: str
    last_name: str
    university: str
    faculty: str
    bio: Optional[str] = None

class GroupCreate(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    creator_id: int

class MessageCreate(BaseModel):
    sender_telegram_id: int
    sender_name: str
    text: str


# --- ЭНДПОИНТЫ ДЛЯ МЕСТ И ОТЗЫВОВ ---

@app.get("/places/")
async def get_places(query: str = None):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if query:
                # Добавлен поиск по адресу, как рекомендовано
                cursor.execute(
                    "SELECT * FROM places WHERE name LIKE ? OR description LIKE ? OR category LIKE ? OR address LIKE ?", 
                    (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%")
                )
            else:
                cursor.execute("SELECT * FROM places")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/places/")
async def add_place(place: PlaceCreate):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO places (name, address, contact_info, description, category, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (place.name, place.address, place.contact_info, place.description, place.category, place.latitude, place.longitude)
            )
            return {"message": "Place added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/places/{place_id}")
async def update_place(place_id: int, place: PlaceCreate):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE places SET name = ?, address = ?, contact_info = ?, description = ?, category = ?, latitude = ?, longitude = ? WHERE id = ?", 
                (place.name, place.address, place.contact_info, place.description, place.category, place.latitude, place.longitude, place_id)
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Place not found")
            return JSONResponse({"message": "Place updated successfully"})
    except HTTPException as he:
        raise he
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/places/{place_id}")
async def delete_place(place_id: int):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM places WHERE id = ?", (place_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Place not found")
            return JSONResponse({"message": "Place deleted successfully"})
    except HTTPException as he:
        raise he
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/places/{place_id}/reviews/")
async def add_review(place_id: int, review: ReviewCreate):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM places WHERE id = ?", (place_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Place not found")

            cursor.execute(
                "INSERT INTO reviews (place_id, author, rating, text) VALUES (?, ?, ?, ?)",
                (place_id, review.author, review.rating, review.text)
            )
            return {"message": "Review added successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/places/{place_id}/reviews/")
async def get_reviews(place_id: int):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reviews WHERE place_id = ?", (place_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ЭНДПОИНТЫ ДЛЯ ПРОФИЛЕЙ ПОЛЬЗОВАТЕЛЕЙ ---

@router.post("/upload-avatar/")
async def upload_avatar(file: UploadFile = File(...)):
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = f"static/avatars/{unique_filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"avatar_url": f"/{file_path}"}

@app.get("/users/")
async def get_users(query: str = None):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if query:
                cursor.execute(
                    "SELECT telegram_id, first_name, last_name, university, faculty, bio FROM users WHERE first_name LIKE ? OR last_name LIKE ? OR university LIKE ? OR faculty LIKE ?",
                    (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%")
                )
            else:
                cursor.execute("SELECT telegram_id, first_name, last_name, university, faculty, bio FROM users")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/")
async def save_profile(user: UserProfileCreate):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user.telegram_id,))
            existing_user = cursor.fetchone()

            if existing_user:
                cursor.execute(
                    "UPDATE users SET first_name = ?, last_name = ?, university = ?, faculty = ?, bio = ? WHERE telegram_id = ?",
                    (user.first_name, user.last_name, user.university, user.faculty, user.bio, user.telegram_id)
                )
            else:
                cursor.execute(
                    "INSERT INTO users (telegram_id, first_name, last_name, university, faculty, bio) VALUES (?, ?, ?, ?, ?, ?)",
                    (user.telegram_id, user.first_name, user.last_name, user.university, user.faculty, user.bio)
                )
            return {"message": "Profile saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{telegram_id}")
async def get_profile(telegram_id: int):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_id, first_name, last_name, university, faculty, bio FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            else:
                raise HTTPException(status_code=404, detail="Profile not found")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ЭНДПОИНТЫ ДЛЯ СООБЩЕСТВ / ГРУПП ---

@app.get("/groups/")
async def get_groups():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM groups")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/groups/")
async def create_group(group: GroupCreate):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO groups (name, category, description, creator_id) VALUES (?, ?, ?, ?)",
                (group.name, group.category, group.description, group.creator_id)
            )
            return {"message": "Group created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/groups/{group_id}/messages/")
async def get_group_messages(group_id: int):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM messages WHERE id = ?", (group_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Group not found")

            cursor.execute(
                "SELECT * FROM messages WHERE group_id = ? ORDER BY id ASC",
                (group_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/groups/{group_id}/messages/")
async def send_group_message(group_id: int, message: MessageCreate):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM groups WHERE id = ?", (group_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Group not found")

            cursor.execute(
                "INSERT INTO messages (group_id, sender_telegram_id, sender_name, text) VALUES (?, ?, ?, ?)",
                (group_id, message.sender_telegram_id, message.sender_name, message.text)
            )
            return {"message": "Message sent successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ГЛАВНАЯ СТРАНИЦА ---

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()