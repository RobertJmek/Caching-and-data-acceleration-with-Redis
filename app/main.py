# API 

from fastapi import FastAPI, HTTPException
from .service import (
    get_movie_with_cache, 
    get_top_movies, 
    update_movie_write_through, 
    delete_movie_write_through, 
    create_movie_write_through,
    seed_theaters,
    find_nearby_theaters
)

from prometheus_fastapi_instrumentator import Instrumentator
import time

limit_top_movies = 10

app = FastAPI(title="Redis Cache Demo")

Instrumentator().instrument(app).expose(app)

@app.get("/")
def read_root():
    return {"status": "API is running", "guide": "Go to /docs for Swagger UI"}

@app.get("/movie/{movie_id}")
async def read_movie(movie_id: str):
    """
    Acesta este endpoint-ul inteligent.
    Măsoară timpul de răspuns pentru a demonstra viteza Redis.
    """
    start_time = time.time()
    
    # Apelăm funcția cu strategie de Cache
    movie, source = get_movie_with_cache(movie_id)
    
    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return {
        "latency_ms": round(duration_ms, 2),
        "source": source,
        "data": movie
    }


#2

@app.get("/top-movies/")
async def get_top_n_movies():
    start_time = time.time()

    movies, source = get_top_movies(limit=limit_top_movies)

    end_time = time.time()

    duration_ms = (end_time - start_time) * 1000

    return {
        "latency_ms": round(duration_ms, 2),
        "source": source,
        "data": movies
    }


# WRITE-THROUGH ENDPOINTS

@app.put("/movie/{movie_id}")
async def update_movie(movie_id: str, update_data: dict):
    """
    WRITE-THROUGH UPDATE:
    Actualizează filmul ATÂT în MongoDB ȘI în Redis cache în același timp.
    Garantează sincronizare perfectă.
    """
    start_time = time.time()
    
    movie, source = update_movie_write_through(movie_id, update_data)
    
    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000

    if not movie:
        raise HTTPException(status_code=404, detail=source)

    return {
        "latency_ms": round(duration_ms, 2),
        "source": source,
        "data": movie
    }


@app.delete("/movie/{movie_id}")
async def delete_movie(movie_id: str):
    """
    WRITE-THROUGH DELETE:
    Șterge filmul din ATÂT MongoDB ȘI Redis cache.
    """
    start_time = time.time()
    
    success, message = delete_movie_write_through(movie_id)
    
    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000

    if not success:
        raise HTTPException(status_code=404, detail=message)

    return {
        "latency_ms": round(duration_ms, 2),
        "message": message
    }


@app.post("/movie/")
async def create_movie(movie_data: dict):
    """
    WRITE-THROUGH CREATE:
    Creează filmul în MongoDB și imediat îl cacheaza în Redis.
    """
    start_time = time.time()
    
    movie, source = create_movie_write_through(movie_data)
    
    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000

    if not movie:
        raise HTTPException(status_code=400, detail=source)

    return {
        "latency_ms": round(duration_ms, 2),
        "source": source,
        "data": movie
    }

# --- GEO ENDPOINTS ---

@app.post("/geo/init")
async def init_geo_data():
    """Buton pentru a încărca datele în Redis."""
    msg = seed_theaters()
    return {"message": msg}

@app.get("/geo/search")
async def search_nearby(lat: float, lon: float, radius: int = 5):
    """Caută cinematografe în apropiere."""
    results = find_nearby_theaters(lat, lon, radius)
    return {
        "center": {"lat": lat, "lon": lon},
        "radius_km": radius,
        "found": len(results),
        "results": results
    }