import json
import datetime
from bson import ObjectId
from .database import db, redis_client

CACHE_TTL = 200 # 5 minute

#1

# --- HELPER: Serializator Custom ---
# Această funcție ajută json.dumps să înțeleagă tipurile speciale din Mongo

def mongo_json_encoder(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# --- HELPER: Curățare obiect pentru FastAPI ---
# FastAPI are propriul encoder, dar e bine să-i dăm date curate 

def clean_mongo_obj(obj):
    if obj is None:
        return None
    # Convertim _id în string direct în obiect
    if "_id" in obj:
        obj["_id"] = str(obj["_id"])
    return obj


def get_movie_no_cache(movie_id: str):
    try:
        oid = ObjectId(movie_id)
    except:
        return None

    movie = db.movies.find_one({"_id": oid})
    return clean_mongo_obj(movie), "MongoDB (Atlas)"


def get_movie_with_cache(movie_id: str):
    cache_key = f"movie:{movie_id}"

    # verificam redis 

    cached_data = redis_client.get(cache_key)
    
    if cached_data:
        print(f"⚡ CACHE HIT pentru {movie_id}")
        return json.loads(cached_data), "Redis"

    # 2. CACHE MISS -> Mongo
    print(f"🐌 CACHE MISS pentru {movie_id}. Citesc din Mongo...")

    movie, source = get_movie_no_cache(movie_id)

    if movie:
        # 3. Scriem în Redis
        redis_client.setex(
            name=cache_key,
            time=CACHE_TTL,
            value=json.dumps(movie, default=mongo_json_encoder)
        )
    
    return movie, source

#2

def get_top_movies(limit=10):

    leaderboard_key = "top_movies:imdb"

    top_ids = redis_client.zrevrange(leaderboard_key, 0, limit - 1) # returneaza ids de la 0 la 9/limita-1

    if top_ids:
        print("⚡ CACHE HIT pentru top movies")
        movies = []
        for movie_id in top_ids:
            movie, source = get_movie_with_cache(str(movie_id))
            if movie:
                movies.append(movie)
        return movies, "Redis ZSET"
    
    print("🐌 CACHE MISS pentru top movies. Citesc din Mongo...")

    top_movies_cursor = db.movies.find(
        {"imdb.rating": {"$ne": ""}},
        {"_id": 1, "imdb.rating": 1}
    ).sort("imdb.rating", -1).limit(limit)

    results = []

    redis_data = {}

    for movie in top_movies_cursor:
        movie_id = str(movie["_id"])
        rating = movie.get("imdb", {}).get("rating", 0)

        if rating:
            redis_data[movie_id] = rating

        full_movie, source = get_movie_with_cache(movie_id)
        results.append(full_movie)

        if redis_data:
            redis_client.zadd(leaderboard_key, redis_data)
            redis_client.expire(leaderboard_key, CACHE_TTL)

    return results, "MongoDB (Atlas)"