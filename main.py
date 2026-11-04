import sqlite3
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Функция для инициализации базы данных при старте
@app.on_event("startup")
def startup_event():
    conn = sqlite3.connect("places.db")
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
            FOREIGN KEY (place_id) REFERENCES places(id)
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
    
    conn.commit()
    conn.close()

# Pydantic-модели
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
    rating: int
    text: str

class UserProfileCreate(BaseModel):
    telegram_id: int
    first_name: str
    last_name: str
    university: str
    faculty: str
    bio: Optional[str] = None


# --- ЭНДПОИНТЫ ДЛЯ МЕСТ И ОТЗЫВОВ ---

@app.get("/places/")
async def get_places(query: str = None):
    try:
        conn = sqlite3.connect("places.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if query:
            cursor.execute(
                "SELECT * FROM places WHERE name LIKE ? OR description LIKE ?", 
                (f"%{query}%", f"%{query}%")
            )
        else:
            cursor.execute("SELECT * FROM places")
            
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/places/")
async def add_place(place: PlaceCreate):
    try:
        conn = sqlite3.connect("places.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO places (name, address, contact_info, description, category, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (place.name, place.address, place.contact_info, place.description, place.category, place.latitude, place.longitude)
        )
        conn.commit()
        conn.close()
        return {"message": "Place added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/places/{place_id}")
async def update_place(place_id: int, place: PlaceCreate):
    try:
        conn = sqlite3.connect("places.db")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE places SET name = ?, address = ?, contact_info = ?, description = ?, category = ?, latitude = ?, longitude = ? WHERE id = ?", 
            (place.name, place.address, place.contact_info, place.description, place.category, place.latitude, place.longitude, place_id)
        )
        conn.commit()
        conn.close()
        return JSONResponse({"message": "Place updated successfully"})
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/places/{place_id}")
async def delete_place(place_id: int):
    try:
        conn = sqlite3.connect("places.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM places WHERE id = ?", (place_id,))
        conn.commit()
        conn.close()
        return JSONResponse({"message": "Place deleted successfully"})
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/places/{place_id}/reviews/")
async def add_review(place_id: int, review: ReviewCreate):
    try:
        conn = sqlite3.connect("places.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reviews (place_id, author, rating, text) VALUES (?, ?, ?, ?)",
            (place_id, review.author, review.rating, review.text)
        )
        conn.commit()
        conn.close()
        return {"message": "Review added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/places/{place_id}/reviews/")
async def get_reviews(place_id: int):
    try:
        conn = sqlite3.connect("places.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reviews WHERE place_id = ?", (place_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ЭНДПОИНТЫ ДЛЯ ПРОФИЛЕЙ ПОЛЬЗОВАТЕЛЕЙ ---

@app.post("/users/")
async def save_profile(user: UserProfileCreate):
    try:
        conn = sqlite3.connect("places.db")
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
        
        conn.commit()
        conn.close()
        return {"message": "Profile saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{telegram_id}")
async def get_profile(telegram_id: int):
    try:
        conn = sqlite3.connect("places.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        else:
            raise HTTPException(status_code=404, detail="Profile not found")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ГЛАВНАЯ СТРАНИЦА ---

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()