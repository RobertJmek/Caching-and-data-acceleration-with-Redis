import json
import datetime
from bson import ObjectId
from .database import db, redis_client

CACHE_TTL = 200 # 5 minute

limit_top_movies = 100

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
        movie = db.movies.find_one({"_id": oid})
    except:
        return None

    return clean_mongo_obj(movie), "MongoDB (Atlas)"


def get_movie_with_cache(movie_id: str):
    cache_key = f"movie:{movie_id}"

    # verificam redis 
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            print(f"⚡ CACHE HIT pentru {movie_id}")
            return json.loads(cached_data), "Redis"
    except Exception as e:
        print(f"⚠️ Redis e jos! Eroare: {e}")
    
    # 2. CACHE MISS -> Mongo
    print(f"🐌 CACHE MISS pentru {movie_id}. Citesc din Mongo...")

    movie, source = get_movie_no_cache(movie_id)

    if movie:
        try:
            redis_client.setex(
                name=cache_key,
                time=CACHE_TTL,
                value=json.dumps(movie, default=mongo_json_encoder)
            )
        except Exception as e:
            print(f"⚠️ Redis e jos! Eroare: {e}")

    return movie, source

#2

def get_top_movies(limit=10):

    leaderboard_key = "top_movies:imdb"

    try:
        top_ids = redis_client.zrevrange(leaderboard_key, 0, limit - 1) # returneaza ids de la 0 la 9/limita-1
        if top_ids:
            print("⚡ CACHE HIT pentru top movies")
            movies = []
            for movie_id in top_ids:
                movie, source = get_movie_with_cache(str(movie_id))
                if movie:
                    movies.append(movie)
            return movies, "Redis ZSET"
    except Exception as e:
        print(f"⚠️ Redis e jos! Eroare: {e}")
    
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
            try:
                redis_client.zadd(leaderboard_key, redis_data)
                redis_client.expire(leaderboard_key, CACHE_TTL)
            except Exception as e:
                print(f"⚠️ Redis e jos! Eroare: {e}")

    return results, "MongoDB (Atlas)"

#3 WRITE-THROUGH STRATEGY

def update_movie_write_through(movie_id: str, update_data: dict):
    """
    WRITE-THROUGH STRATEGY:
    Scrie ATÂT în Cache (Redis) ȘI în Database (MongoDB) în același timp.
    Garantează că cache și database sunt ÎNTOTDEAUNA în sincronizare.
    """
    try:
        oid = ObjectId(movie_id)
    except:
        return None, "Invalid movie ID"

    # 1. Update în MongoDB ÎNTÂI (pentru siguranță)
    try:
        result = db.movies.update_one(
            {"_id": oid},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            return None, "Movie not found in MongoDB"
        
        print(f"✅ Datele au fost update în MongoDB pentru {movie_id}")
    except Exception as e:
        return None, f"MongoDB error: {e}"

    # 2. Aduna datele complete din MongoDB (pentru a le casha)
    try:
        movie = db.movies.find_one({"_id": oid})
        if movie:
            cache_key = f"movie:{movie_id}"
            
            # 3. Scrie în Cache
            redis_client.setex(
                name=cache_key,
                time=CACHE_TTL,
                value=json.dumps(clean_mongo_obj(movie), default=mongo_json_encoder)
            )
            print(f"✅ Datele au fost update în Redis cache pentru {movie_id}")
            
            return clean_mongo_obj(movie), "Write-Through: Updated in MongoDB & Redis"
    except Exception as e:
        return None, f"Redis cache error: {e}"

    return None, "Unknown error"


def delete_movie_write_through(movie_id: str):
    """
    WRITE-THROUGH DELETE:
    Șterge datele ATÂT din Cache ȘI din Database.
    """
    try:
        oid = ObjectId(movie_id)
    except:
        return False, "Invalid movie ID"

    # 1. Șterge din MongoDB
    try:
        result = db.movies.delete_one({"_id": oid})
        
        if result.deleted_count == 0:
            return False, "Movie not found in MongoDB"
        
        print(f"✅ Filmul a fost șters din MongoDB")
    except Exception as e:
        return False, f"MongoDB error: {e}"

    # 2. Șterge din Cache
    try:
        cache_key = f"movie:{movie_id}"
        redis_client.delete(cache_key)
        print(f"✅ Filmul a fost șters din Redis cache")
        return True, "Write-Through: Deleted from MongoDB & Redis"
    except Exception as e:
        return False, f"Redis error: {e}"


def create_movie_write_through(movie_data: dict):
    """
    WRITE-THROUGH CREATE:
    Creează filmul în MongoDB și imediat îl cacheaza în Redis.
    """
    try:
        # 1. Insert în MongoDB
        result = db.movies.insert_one(movie_data)
        movie_id = str(result.inserted_id)
        
        print(f"✅ Filmul a fost creat în MongoDB cu ID: {movie_id}")
        
        # 2. Adună datele complete (cu _id)
        movie = db.movies.find_one({"_id": result.inserted_id})
        
        if movie:
            cache_key = f"movie:{movie_id}"
            
            # 3. Scrie în Cache
            redis_client.setex(
                name=cache_key,
                time=CACHE_TTL,
                value=json.dumps(clean_mongo_obj(movie), default=mongo_json_encoder)
            )
            print(f"✅ Filmul a fost salvat în Redis cache")
            
            return clean_mongo_obj(movie), "Write-Through: Created in MongoDB & Redis"
    except Exception as e:
        return None, f"Error: {e}"
    
#4 GEO Indexing for Theaters
    
def seed_theaters():
    key = "theaters:bucharest"
    
    # Format: (Longitudine, Latitudine, Nume)
    # Atenție: Redis cere Longitudine PRIMA, apoi Latitudine
    locations = [
        (26.0534, 44.4304, "Cinema City AFI Cotroceni"),
        (26.0963, 44.4268, "Cinema City Sun Plaza"),
        (26.0883, 44.4933, "Grand Cinema Baneasa"),
        (26.1202, 44.4206, "Hollywood Multiplex"),
        (26.0145, 44.4355, "Cinema Plaza Romania"),
        (26.1025, 44.4410, "Cinema Elvire Popesco (Centru)")
    ]
    
    try:
        # Ștergem cheia veche ca să nu duplicăm
        redis_client.delete(key)
        
        # Adăugăm punctele
        count = redis_client.geoadd(key, [coord for loc in locations for coord in loc])
        return f"Am adăugat {count} cinematografe în Redis GeoIndex."
    except Exception as e:
        return f"Eroare Redis Geo: {e}"

def find_nearby_theaters(lat: float, lon: float, radius_km: int):
    """
    Caută cinematografe pe o rază dată.
    Folosește GEOSEARCH (disponibil în Redis 6.2+).
    """
    key = "theaters:bucharest"
    
    try:
        # Căutăm puncte în raza specificată
        results = redis_client.geosearch(
            name=key,
            longitude=lon,
            latitude=lat,
            radius=radius_km,
            unit='km',
            withdist=True,  # Vrem și distanța
            withcoord=True, # Vrem și coordonatele (pt hartă)
            sort='ASC'      # Cele mai apropiate primele
        )
        
        # Formatăm frumos rezultatul pentru API
        clean_results = []
        for res in results:
            # res arată așa: ['Nume', distanta, (lon, lat)]
            name = res[0]
            dist = res[1]
            coords = res[2]
            
            clean_results.append({
                "name": name,
                "distance_km": round(dist, 2),
                "latitude": coords[1],  # Streamlit vrea Latitudine
                "longitude": coords[0]  # Streamlit vrea Longitudine
            })
            
        return clean_results
    except Exception as e:
        print(f"Geo Error: {e}")
        return []
    
def cache_movie_as_hash(movie_id: str, movie_data: dict):
    """
    Stochează doar câmpurile esențiale într-un Hash Redis.
    Avantaj: Putem citi doar titlul fără să descărcăm tot JSON-ul.
    """
    key = f"movie:hash:{movie_id}"
    
    # Redis Hashes sunt plate, deci luăm doar câmpurile de top

    mapping = {
        "title": str(movie_data.get('title', 'N/A')),
        "year": str(movie_data.get('year', 'N/A')),
        "genres": str(movie_data.get('genres', [])),
        "director": str(movie_data.get('directors', ['Unknown'])[0])
    }
    
    try:
        redis_client.hset(key, mapping=mapping)
        redis_client.expire(key, CACHE_TTL) 
        return "Saved to Hash"
    except Exception as e:
        return str(e)

def get_movie_hash_preview(movie_id: str):
    """Citește doar hash-ul (rapid preview)."""
    return redis_client.hgetall(f"movie:hash:{movie_id}")


    
def get_top_movies_optimized(limit=limit_top_movies):
    leaderboard_key = "leaderboard:top_movies_opt"
    
    # 1. Verificăm dacă avem date în Redis
    top_ids = redis_client.zrevrange(leaderboard_key, 0, limit - 1)
    
    source_msg = "Redis (ZSET + Hash Pipeline)"
    
    # 2. Dacă e gol, facem Seed ACUM
    if not top_ids:
        success = seed_optimized_cache(limit + 10) 
        if success:
            # Încercăm să citim iar după seed
            top_ids = redis_client.zrevrange(leaderboard_key, 0, limit - 1)
            source_msg = "MongoDB -> Redis (Just Seeded)"
        else:
            return [], "MongoDB Empty"

    # 3. Luăm detaliile prin Pipeline (Fast Fetch)
    pipe = redis_client.pipeline()
    for mid in top_ids:
        if isinstance(mid, bytes):
            mid = mid.decode('utf-8')
        pipe.hgetall(f"movie:hash:{mid}")
        
    hash_results = pipe.execute()
    
    # 4. Construim răspunsul
    final_list = []

    def ensure_str(value):
        return value.decode('utf-8') if isinstance(value, bytes) else value
    

    for mid, data in zip(top_ids, hash_results):
        if data:
            # Convertim bytes -> string
            clean_obj = {ensure_str(k): ensure_str(v) for k, v in data.items()}
            # Adăugăm ID-ul manual
            clean_obj['_id'] = ensure_str(mid)
            final_list.append(clean_obj)
            
    return final_list, source_msg


def seed_optimized_cache(limit=limit_top_movies):
    print("⚙️ Seeding Optimized Cache...")
    # Luăm filmele cu rating bun din Mongo
    pipeline = [
        {"$match": {"imdb.rating": {"$ne": ""}}}, 
        {"$sort": {"imdb.rating": -1}}, 
        {"$limit": limit}
    ]
    movies = list(db.movies.aggregate(pipeline))
    
    pipe = redis_client.pipeline()
    leaderboard_key = "leaderboard:top_movies_opt"
    
    for m in movies:
        mid = str(m['_id'])
        # 1. Creăm Hash-ul (Doar date esențiale)
        hash_key = f"movie:hash:{mid}"
        mapping = {
            "title": str(m.get('title', 'N/A')),
            "year": str(m.get('year', 'N/A')),
            "rating": str(m.get('imdb', {}).get('rating', 0)),
            "poster": str(m.get('poster', '')) # Opțional, pt UI
        }
        pipe.hset(hash_key, mapping=mapping)
        pipe.expire(hash_key, CACHE_TTL)
        
        # 2. Adăugăm în Sorted Set (ID + Scor)
        # Redis ZADD syntax: nume_cheie, {membru: scor}
        try:
            score = float(mapping['rating'])
            pipe.zadd(leaderboard_key, {mid: score})
        except:
            pass
            
    pipe.execute()
    return True