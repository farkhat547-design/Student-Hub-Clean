from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import sqlite3
from typing import Optional
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.on_event("startup")
def startup_event():
    conn = sqlite3.connect("places.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            address TEXT,
            contact_info TEXT,
            description TEXT
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

# Pydantic-модель для валидации отзывов
class ReviewCreate(BaseModel):
    author: str
    rating: int
    text: str

# Подключение к SQLite базе данных
conn = sqlite3.connect("places.db", check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы, если она не существует
cursor.execute('''
    CREATE TABLE IF NOT EXISTS places (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        contact_info TEXT,
        description TEXT
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id INTEGER NOT NULL,
        author TEXT NOT NULL,
        rating INTEGER NOT NULL,
        text TEXT NOT NULL,
        FOREIGN KEY (place_id) REFERENCES places(id)
    )
''')
conn.commit()

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

# Эндпоинт для добавления нового места (возвращаем его на место)
@app.post("/places/")
async def add_place(place: PlaceCreate):
    try:
        conn = sqlite3.connect("places.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO places (name, address, contact, description, category, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (place.name, place.address, place.contact, place.description, place.category, place.latitude, place.longitude)
        )
        conn.commit()
        conn.close()
        return {"message": "Place added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Update an existing place
@app.put("/places/{place_id}")
async def update_place(place_id: int, place: PlaceCreate):
    try:
        cursor.execute("UPDATE places SET name = ?, address = ?, contact_info = ?, description = ? WHERE id = ?", (place.name, place.address, place.contact_info, place.description, place_id))
        conn.commit()
        return JSONResponse({"message": "Place updated successfully"})
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))

# Delete a place
@app.delete("/places/{place_id}")
async def delete_place(place_id: int):
    try:
        cursor.execute("DELETE FROM places WHERE id = ?", (place_id,))
        conn.commit()
        return JSONResponse({"message": "Place deleted successfully"})
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))

# Create a new review for a place
@app.post("/places/{place_id}/reviews/")
async def add_review(place_id: int, review: ReviewCreate):
    try:
        cursor.execute(
            "INSERT INTO reviews (place_id, author, rating, text) VALUES (?, ?, ?, ?)",
            (place_id, review.author, review.rating, review.text)
        )
        conn.commit()
        conn.close()
        return {"message": "Review added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get all reviews for a place
@app.get("/places/{place_id}/reviews/")
async def get_reviews(place_id: int):
    try:
        cursor.execute("SELECT * FROM reviews WHERE place_id = ?", (place_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()