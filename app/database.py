import os
from dotenv import load_dotenv
from pymongo import MongoClient
import redis

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
REDIS_HOST = os.getenv("REDIS_HOST", "redis") 
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


mongo_client = MongoClient(MONGO_URL)

db = mongo_client["sample_mflix"] 


redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True 
)

if not MONGO_URL:
    print("⚠️ ATENȚIE: MONGO_URL nu a fost găsit în .env!")


if __name__ == "__main__":
    print("🚀 Începem testarea conexiunilor...")

    # 1. Testare MongoDB
    try:
        print("⏳ Verific conexiunea cu MongoDB Atlas...")
        # Încercăm o comandă simplă: ping
        mongo_client.admin.command('ping')
        print("✅ MongoDB: CONECTAT cu succes!")
        
        # Verificăm dacă vedem colecțiile din sample_mflix
        cols = db.list_collection_names()
        print(f"   📂 Colecții găsite ({len(cols)}): {cols[:3]} ...")
        
    except Exception as e:
        print(f"❌ MongoDB: Eroare critică - {e}")

    # 2. Testare Redis
    try:
        print("⏳ Verific conexiunea cu Redis...")
        # Comanda PING -> ar trebui să răspundă PONG
        if redis_client.ping():
            print("✅ Redis: CONECTAT cu succes! (Răspuns: PONG)")
            
            # Test scriere/citire
            redis_client.set("test_key", "Salut din Python")
            val = redis_client.get("test_key")
            print(f"   💾 Test Scriere/Citire: {val}")
            
    except Exception as e:
        print(f"❌ Redis: Nu mă pot conecta. (Este containerul pornit? Ești pe localhost?) - {e}")

