import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
import json

limit_top_movies = 100

# Configurare pagină
st.set_page_config(page_title="Redis Cache Demo", page_icon="⚡", layout="wide")

st.title("⚡ Redis Data Acceleration Demo")
st.markdown("Proiect T4 - Comparatie de performanță: **MongoDB Atlas** vs **Redis Local**")

# Tabs pentru diferite strategii
tabs = st.tabs(["🔍 Citire (Read-Through)", "✍️ Scriere (Write-Through)", "🏆 Top Filme", "🧪 Invalidation Lab"])

# --- TAB 1: READ STRATEGY ---
with tabs[0]:
    st.header("🔍 Citire filme cu caching")
    
    # Input pentru ID-ul filmului
    # Default ID: Unul valid din sample_mflix
    movie_id = st.text_input("Introdu ID-ul filmului (MongoDB _id):", value="573a1390f29313caabcd4803", key="read_movie_id")

    # Buton de căutare
    if st.button("🔍 Caută Film", key="search_btn"):
        if not movie_id:
            st.warning("Te rog introdu un ID valid.")
        else:
            # Facem request către propriul nostru API
            try:
                # NOTA: API-ul ruleaza pe portul 8000
                response = requests.get(f"http://127.0.0.1:8000/movie/{movie_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    latency = data['latency_ms']
                    source = data['source']
                    movie_data = data['data']

                    # --- AFISARE METRICI ---
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(label="Sursa Datelor", value=source)
                    
                    with col2:
                        # Colorăm diferit în funcție de sursă
                        delta_color = "normal" if source == "Redis" else "inverse"
                        st.metric(label="Latență (ms)", value=f"{latency} ms", delta=f"{latency} ms", delta_color=delta_color)
                    
                    with col3:
                        st.metric(label="Status", value="Succes ✅")

                    # --- AFISARE DETALII FILM ---
                    st.divider()
                    c1, c2 = st.columns([1, 2])
                    
                    with c1:
                        if "poster" in movie_data and movie_data["poster"]:
                            st.image(movie_data["poster"], width=300)
                        else:
                            st.info("Fără poster disponibil")
                    
                    with c2:
                        st.header(movie_data.get("title", "Titlu necunoscut"))
                        st.markdown(f"**An:** {movie_data.get('year')} | **Rating IMDB:** {movie_data.get('imdb', {}).get('rating')}")
                        st.write(f"**Plot:** {movie_data.get('plot')}")
                        st.write(f"**Genuri:** {', '.join(movie_data.get('genres', []))}")
                        st.caption(f"Cached at: {movie_data.get('lastupdated', 'N/A')}")
                        
                        # Afișăm JSON-ul brut într-un expander
                        with st.expander("Vezi JSON brut"):
                            st.json(movie_data)

                else:
                    st.error(f"Eroare API: {response.status_code} - Filmul nu a fost găsit.")
            
            except Exception as e:
                st.error(f"Nu pot contacta API-ul. Asigură-te că rulează pe portul 8000. Eroare: {e}")

# --- TAB 2: WRITE-THROUGH STRATEGY ---
with tabs[1]:
    st.header("✍️ Scriere cu Write-Through Strategy")
    st.markdown("Actualizează, creează sau șterge filme. Datele vor fi scrise **simultan** în MongoDB și Redis.")
    
    write_action = st.radio("Alege acțiunea:", ["📝 Actualizare film", "➕ Creare film nou", "🗑️ Ștergere film"], horizontal=True)
    
    # --- ACTUALIZARE FILM ---
    if write_action == "📝 Actualizare film":
        st.subheader("Actualizează un film existent")
        
        col1, col2 = st.columns(2)
        with col1:
            movie_id_update = st.text_input("ID-ul filmului de actualizat:", value="573a1390f29313caabcd4803", key="update_id")
        
        with col2:
            st.write("")  # spacing
        
        st.write("**Câmpurile pe care le poți actualiza:**")
        col_a, col_b = st.columns(2)
        
        with col_a:
            title = st.text_input("Titlu (opțional):", key="update_title")
            year = st.number_input("An (opțional):", value=0, step=1, key="update_year")
            rating = st.number_input("Rating IMDB (opțional):", value=0.0, step=0.1, key="update_rating")
        
        with col_b:
            plot = st.text_area("Plot (opțional):", key="update_plot")
            genres = st.text_input("Genuri (separa cu virgulă, opțional):", key="update_genres")
        
        if st.button("✅ Actualizează film", key="update_btn"):
            update_data = {}
            if title:
                update_data["title"] = title
            if year > 0:
                update_data["year"] = year
            if rating > 0:
                update_data["imdb.rating"] = rating
            if plot:
                update_data["plot"] = plot
            if genres:
                update_data["genres"] = [g.strip() for g in genres.split(",")]
            
            if not update_data:
                st.warning("Introdu cel puțin un câmp pentru actualizare.")
            else:
                try:
                    response = requests.put(
                        f"http://127.0.0.1:8000/movie/{movie_id_update}",
                        json=update_data
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ Film actualizat cu succes! (Latență: {data['latency_ms']}ms)")
                        st.info(f"Sursa: {data['source']}")
                        with st.expander("Vezi datele actualizate"):
                            st.json(data['data'])
                    else:
                        st.error(f"❌ Eroare: {response.status_code} - {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"❌ Eroare conexiune: {e}")
    
    # --- CREARE FILM NOU ---
    elif write_action == "➕ Creare film nou":
        st.subheader("Creează un film nou")
        
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Titlu (necesar):", key="create_title")
            year = st.number_input("An:", value=2024, step=1, key="create_year")
            rating = st.number_input("Rating IMDB:", value=7.0, step=0.1, key="create_rating")
        
        with col2:
            plot = st.text_area("Plot:", key="create_plot")
            genres = st.text_input("Genuri (separa cu virgulă):", value="Drama", key="create_genres")
            poster = st.text_input("URL Poster (opțional):", key="create_poster")
        
        if st.button("➕ Creează film", key="create_btn"):
            if not title:
                st.warning("Titlul este obligatoriu!")
            else:
                movie_data = {
                    "title": title,
                    "year": year,
                    "plot": plot,
                    "genres": [g.strip() for g in genres.split(",")],
                    "imdb": {"rating": rating},
                }
                if poster:
                    movie_data["poster"] = poster
                
                try:
                    response = requests.post(
                        "http://127.0.0.1:8000/movie/",
                        json=movie_data
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ Film creat cu succes! (Latență: {data['latency_ms']}ms)")
                        st.info(f"Sursa: {data['source']}")
                        st.write(f"**ID-ul noului film:** `{data['data']['_id']}`")
                        with st.expander("Vezi filmul creat"):
                            st.json(data['data'])
                    else:
                        st.error(f"❌ Eroare: {response.status_code} - {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"❌ Eroare conexiune: {e}")
    
    # --- ȘTERGERE FILM ---
    elif write_action == "🗑️ Ștergere film":
        st.subheader("Șterge un film")
        
        movie_id_delete = st.text_input("ID-ul filmului de șters:", value="573a1390f29313caabcd4803", key="delete_id")
        
        col1, col2, col3 = st.columns(3)
        with col2:
            if st.button("🗑️ Șterge film", key="delete_btn"):
                try:
                    response = requests.delete(
                        f"http://127.0.0.1:8000/movie/{movie_id_delete}"
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ Film șters cu succes! (Latență: {data['latency_ms']}ms)")
                        st.info(f"Mesaj: {data['message']}")
                    else:
                        st.error(f"❌ Eroare: {response.status_code} - {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"❌ Eroare conexiune: {e}")

# --- TAB 3: TOP FILME ---
with tabs[2]:
    st.header("🏆 Top " + str(limit_top_movies) + " Filme (Redis Sorted Sets)")
    st.markdown("Compară performanța între abordarea clasică (JSON întreg) și cea optimizată (Redis Hashes + Pipelining).")

    col_std, col_opt = st.columns(2)

    with col_std:
        st.subheader("📊 Standard Approach")
        st.markdown("Returnează top filme ca JSON complet din Redis.")
    if st.button("🔄 Încarcă Top Filme", key="top_btn"):
        try:
            response = requests.get("http://127.0.0.1:8000/top-movies")
            if response.status_code == 200:
                res_json = response.json()
                movies = res_json['data']
                latency = res_json['latency_ms']
                
                st.caption(f"⏱️ Timp încărcare top: **{latency} ms**")
                
                # Afișăm filmele într-un grid
                for i, movie in enumerate(movies):
                    # Facem coloane pentru fiecare film
                    with st.container():
                        c1, c2 = st.columns([1, 5])
                        with c1:
                            st.subheader(f"#{i+1}")
                            if "poster" in movie and movie["poster"]:
                                st.image(movie["poster"], width=80)
                        with c2:
                            st.write(f"**{movie.get('title')}**")
                            st.write(f"⭐ {movie.get('imdb', {}).get('rating')} | 📅 {movie.get('year')}")
                        st.divider()
            else:
                st.error("Eroare la încărcarea topului.")
                
        except Exception as e:
            st.error(f"Eroare conexiune: {e}")

    with col_opt:
        st.subheader("🚀 Optimized Approach")
        st.markdown("Returnează top filme folosind Redis Hashes și Pipelining pentru performanță maximă.")
    if st.button("🔄 Încarcă Top Filme Optimizat", key="top_opt_btn"):
        try:
            response = requests.get("http://127.0.0.1:8000/top-movies-optimized")
            if response.status_code == 200:
                data = response.json()
                latency = data['latency_ms']
                source = data['source']
                movie_data = data['data']
                
                st.caption(f"⏱️ Timp încărcare top: **{latency} ms**")
                # Afișăm filmele într-un grid
                st.metric("Latency", f"{data['latency_ms']} ms", delta="- Optimized", delta_color="normal")
                st.success(f"Source: {data['source']}")
                
                # Afișăm datele (care vin din Hash)
                for m in data['data']:
                    st.write(f"**{m.get('title')}** (⭐ {m.get('rating')})")
        except Exception as e:
                st.error(f"Err: {e}")
            
# --- TAB 4: INVALIDATION LAB ---
with tabs[3]:
    st.header("🧪 Cache Invalidation & Stale Data Simulation")
    st.markdown("""
    Aici vom demonstra ce se întâmplă când datele din Baza de Date se schimbă, dar Cache-ul rămâne în urmă (**Stale Data**).
    """)

    # Folosim un ID fix pentru experiment ca să fie ușor
    test_id = st.text_input("ID Film Experiment:", value="573a1390f29313caabcd4803", key="inv_id")
    
    col1, col2, col3 = st.columns(3)
    
    # --- PASUL 1: CITEȘTE STAREA CURENTĂ ---
    with col1:
        st.subheader("1. Starea Curentă")
        if st.button("🔍 Citește Film (Prin API)", key="step1_btn"):
            res = requests.get(f"http://127.0.0.1:8000/movie/{test_id}")
            if res.status_code == 200:
                data = res.json()
                st.info(f"Titlu primit: **{data['data']['title']}**")
                st.caption(f"Sursa: {data['source']}")
                if "Redis" in data['source']:
                    st.success("✅ Cache HIT")
                else:
                    st.warning("⚠️ Cache MISS (Data loaded from Mongo)")
            else:
                st.error("Film negăsit")

    # --- PASUL 2: CREEAZĂ PROBLEMA (STALE DATA) ---
    with col2:
        st.subheader("2. Creează Inconsistență")
        new_title = st.text_input("Noul Titlu (Backdoor):", value="TITLU MODIFICAT DE HACKER", key="hacker_title")
        
        if st.button("😈 Backdoor Update (Only Mongo)", key="step2_btn"):
            # Apelăm endpoint-ul care ignoră Redis
            requests.post(f"http://127.0.0.1:8000/simulate/backdoor-update/{test_id}?new_title={new_title}")
            st.warning("⚠️ Mongo a fost actualizat!")
            st.write("Redis NU știe de această modificare.")
            st.write("Dacă apeși din nou pe Pasul 1, vei primi tot titlul VECHI din Redis.")

    # --- PASUL 3: REZOLVĂ PROBLEMA (INVALIDARE) ---
    with col3:
        st.subheader("3. Strategii de Rezolvare")
        
        st.markdown("**Opțiunea A: Așteaptă TTL**")
        st.caption("Așteaptă 5 minute să expire singur.")
        
        st.markdown("**Opțiunea B: Invalidare Manuală**")
        if st.button("🧹 Force Cache Invalidation", key="step3_btn"):
            requests.delete(f"http://127.0.0.1:8000/simulate/invalidate/{test_id}")
            st.success("🗑️ Cheia a fost ștearsă din Redis!")
            st.write("Dacă apeși pe Pasul 1, vei primi titlul NOU (Mongo).")
# --- SECTIUNE DE MONITORIZARE ---

st.divider()
st.subheader("📊 Informații despre strategii")

col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.markdown("""
    **Read-Through**
    - ✅ Cărcare automată din BD
    - ✅ Cache transparent
    - ⚠️ Latență inițială mai mare
    """)

with col_info2:
    st.markdown("""
    **Write-Through**
    - ✅ Scriere sincronizată
    - ✅ Nicio stare inconsistentă
    - ⚠️ Latență mai mare la scriere
    """)

with col_info3:
    st.markdown("""
    **Redis Benefits**
    - ⚡ Citire instantanee
    - 💾 Menos congestie DB
    - 🚀 Scalabilitate superioară
    """)

#4 <iframe src="http://localhost:3000/d-solo/ff123456/movie-api-cache-performance?orgId=1&from=1769092191931&to=1769092491931&timezone=browser&var-DS_PROMETHEUS=afay1uw6uhiwwe&refresh=5s&theme=dark&panelId=panel-3&__feature.dashboardSceneSolo=true" width="450" height="200" frameborder="0"></iframe>


st.divider()
st.subheader("📈 Real-Time Performance (Grafana Embed)")

# Creăm 2 coloane pentru grafice
g_col1, g_col2 = st.columns(2)

with g_col1:
    st.markdown("**Latency GET /movie/{id}**")
    components.iframe(
        src="http://localhost:3000/d-solo/endpoint_focused_v1/movie-api-focused-view?orgId=1&timezone=browser&var-DS_PROMETHEUS=afay1uw6uhiwwe&refresh=5s&panelId=panel-1&__feature.dashboardSceneSolo=true",
        height=300,
        scrolling=False
    )

with g_col2:
    st.markdown("**Latency GET /top-movies**")
    # ÎNLOCUIEȘTE URL-ul de mai jos cu cel copiat de tine pentru Panel-ul 2 (Latency)
    components.iframe(
        src="http://localhost:3000/d-solo/endpoint_focused_v1/movie-api-focused-view?orgId=1&timezone=browser&var-DS_PROMETHEUS=afay1uw6uhiwwe&refresh=5s&panelId=panel-3&__feature.dashboardSceneSolo=true",
        height=300,
        scrolling=False
    )


st.divider()
st.header("🌍 Redis Geospatial Search")

st.info("Redis poate stoca coordonate GPS și face căutări pe rază extrem de rapid.")

# Buton de initializare
if st.button("📍 Inițializează Harta (Load Data)"):
    res = requests.post("http://127.0.0.1:8000/geo/init")
    st.success(res.json().get("message"))

# Controale pentru utilizator
col_geo1, col_geo2 = st.columns(2)

with col_geo1:
    # Coordonatele Universității București (Default)
    my_lat = st.number_input("Latitudine", value=44.4350, format="%.4f")
    my_lon = st.number_input("Longitudine", value=26.1000, format="%.4f")

with col_geo2:
    radius = st.slider("Raza de căutare (km)", 1, 20, 5)

if st.button("🔍 Caută Cinematografe"):
    try:
        # Facem request la API
        response = requests.get(f"http://127.0.0.1:8000/geo/search?lat={my_lat}&lon={my_lon}&radius={radius}")
        data = response.json()
        
        results = data['results']
        st.write(f"Am găsit **{len(results)}** locații pe o rază de {radius}km.")
        
        if results:
            # Pregătim datele pentru harta Streamlit
            # Adăugăm și punctul nostru (Eu) ca să vedem unde suntem
            my_location = {"latitude": my_lat, "longitude": my_lon, "name": "📍 TU EȘTI AICI", "color": "#FF0000"}
            
            # Mapam rezultatele
            map_data = []
            map_data.append(my_location)
            
            for r in results:
                map_data.append({
                    "latitude": r['latitude'],
                    "longitude": r['longitude'],
                    "name": r['name'],
                    "color": "#0000FF" # Albastru pt cinematografe
                })
            
            # Convertim la DataFrame pentru st.map
            df = pd.DataFrame(map_data)
            
            # Afișăm harta
            st.map(df, latitude="latitude", longitude="longitude", size=20, zoom=11)
            
            # Afișăm și lista text
            st.table(pd.DataFrame(results)[['name', 'distance_km']])
            
    except Exception as e:
        st.error(f"Eroare: {e}")

