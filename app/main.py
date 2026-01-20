# API 

from fastapi import FastAPI, HTTPException
from .service import get_movie_with_cache, get_top_movies
import time

limit_top_movies = 10 

app = FastAPI(title="Redis Cache Demo")

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

