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
    conn.commit()
    conn.close()

# Pydantic-модель для валидации данных
class PlaceCreate(BaseModel):
    name: str
    address: str
    contact_info: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# Pydantic-модель для валидации отзывов
class ReviewCreate(BaseModel):
    author: str
    rating: int
    text: str

# Эндпоинт для получения всех мест (с поиском по query)
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

# Эндпоинт для добавления нового места
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

# Обновление существующего места
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

# Удаление места
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

# Добавление отзыва для места
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

# Получение всех отзывов для места
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

# Главная страница HTML
@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()