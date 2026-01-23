from locust import HttpUser, task, between
import random

MOVIE_IDS = [
    "573a1390f29313caabcd42e8", # The Great Train Robbery
    "573a1390f29313caabcd446f", # A Corner in Wheat
    "573a1390f29313caabcd4803", # Winsor McCay
]

class WebsiteUser(HttpUser):
    # Timpul de așteptare între request-uri (simulăm un om real)
    wait_time = between(1, 2)

    @task(3) # Ponderea 3: De 3 ori mai probabil să ceară un film specific
    def view_movie(self):
        movie_id = random.choice(MOVIE_IDS)
        self.client.get(f"/movie/{movie_id}", name="/movie/{id}")

    @task(1) # Ponderea 1: Mai rar se uită la top
    def view_top_movies(self):
        self.client.get("/top-movies", name="/top-movies")