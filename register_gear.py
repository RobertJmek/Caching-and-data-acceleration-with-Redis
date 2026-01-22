#can't really do this cuz I'm on a mac but here is the code


import redis
import os
from dotenv import load_dotenv

load_dotenv()

# Conexiune la Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# URL-ul Mongo trebuie hardcodat în scriptul trimis la Redis sau citit din ENV în interior
# Pentru simplitate, îl injectăm direct în string-ul scriptului
MONGO_URL = os.getenv("MONGO_URL")

# --- CODUL CARE VA RULA ÎN INTERIORUL REDIS ---
gears_script = f"""
import json
import pymongo
from bson import ObjectId

# Funcția helper pentru serializare (aceeași problemă cu ObjectId)
def my_encoder(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    return str(obj)

def read_through_movie(record):
    # 'record' este argumentul primit de la trigger
    movie_id = record[1]
    cache_key = 'movie:' + movie_id
    
    # 1. Verificăm dacă există deja în Redis (accesăm memoria locală)
    # execute('GET', ...) este comanda internă Redis
    cached_val = execute('GET', cache_key)
    if cached_val:
        # Log-ul apare în consola Docker a Redis-ului
        log(f"RedisGears: CACHE HIT pentru {{movie_id}}")
        return cached_val

    # 2. Dacă nu, ne conectăm la Mongo (din interiorul Redis!)
    log(f"RedisGears: CACHE MISS. Conectare la Atlas pentru {{movie_id}}...")
    
    try:
        client = pymongo.MongoClient("{MONGO_URL}")
        db = client['sample_mflix']
        
        # Căutăm filmul
        doc = db.movies.find_one({{"_id": ObjectId(movie_id)}})
        
        if doc:
            # Curățăm obiectul
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            
            # Serializăm
            json_data = json.dumps(doc, default=my_encoder)
            
            # 3. Scriem în Cache (pentru data viitoare)
            execute('SETEX', cache_key, 60, json_data)
            
            log("RedisGears: Date aduse din Mongo si salvate in Cache.")
            return json_data
        else:
            return None
            
    except Exception as e:
        log(f"RedisGears ERROR: {{str(e)}}")
        return None

# Înregistram trigger-ul
# Când apelăm 'RG.TRIGGER get_movie_rt <id>', se execută funcția asta
gb = GearsBuilder()
gb.map(read_through_movie)
gb.register(trigger='get_movie_rt', requirements=['pymongo', 'dnspython'])
"""

print("🚀 Trimit scriptul către RedisGears...")
try:
    # Comanda magică care trimite codul Python în Redis
    r.execute_command('RG.PYEXECUTE', gears_script)
    print("✅ Script înregistrat cu succes! Redis este acum un Read-Through Cache.")
except Exception as e:
    print(f"❌ Eroare: {e}")

