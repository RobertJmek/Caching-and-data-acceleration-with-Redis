import streamlit as st
import requests
import pandas as pd
import plotly.express as px

limit_top_movies = 10

# Configurare pagină
st.set_page_config(page_title="Redis Cache Demo", page_icon="⚡", layout="wide")

st.title("⚡ Redis Data Acceleration Demo")
st.markdown("Proiect T4 - Comparatie de performanță: **MongoDB Atlas** vs **Redis Local**")

# Input pentru ID-ul filmului
# Default ID: Unul valid din sample_mflix
movie_id = st.text_input("Introdu ID-ul filmului (MongoDB _id):", value="573a1390f29313caabcd4803")

# Buton de căutare
if st.button("🔍 Caută Film"):
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

#2 

st.header("🏆 Top " + str(limit_top_movies) + " Filme (Redis Sorted Sets)")

if st.button("🔄 Încarcă Top Filme"):
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

# --- SECTIUNE DE MONITORIZARE (Va urma) ---

st.divider()
st.subheader("📊 Statistici în timp real")
st.info("Aici vom integra graficele din Prometheus/Grafana în pașii următori.")