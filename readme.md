1. INTRODUCTION

This project demonstrates how to integrate Redis as a high-performance caching layer to accelerate data retrieval from a persistent database (MongoDB Atlast). 

By implementing various caching strategies(Cache Aside, Write-Through), and advanced data strunctures(Sorted Sets, Sorted Hashes, Geospatial Indexes), we aim to reduce query latency, lower the load on the primary database, and improve overall system scalability.

2: SYSTEM ARCHITECTURE

 2.1 High Level Application DIAGRAM illustrates the Hybrid Cloud setup:

Initially made by me using www.plantuml.com [1], revized visually by Gemini 3 PRO on 23.01.2026 and converted to mermaid to be easily seen on GitHub.

```mermaid
---
config:
  theme: mc
---
graph TD

    classDef ui fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#000000;
    classDef app fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000000;
    classDef config fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#000000;
    classDef db fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000000;
    classDef tool fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000000;
    classDef cloud fill:#f5f5f5,stroke:#9e9e9e,stroke-width:2px,stroke-dasharray: 5 5,color:#000000;

    subgraph Cloud_Infrastructure [☁️ Cloud Infrastructure]
        direction TB
        Mongo[(MongoDB Atlas)]:::db
    end


    subgraph Docker_Network [ Localhost + Docker]
        direction TB
        
        subgraph User_Interfaces [Frontend local]
            UI[Streamlit UI]:::ui
        end

        subgraph Application [Backend local]
            subgraph Backend [FastAPI]
                Main[main.py]:::app
                Service[service.py]:::app
                DB_Mod[database.py]:::config
            end
        end

        subgraph Local_Data [Cache Container]
            Redis[(Redis)]:::db
        end

        subgraph Telemetry [Monitoring Containers]
            Prom[Prometheus]:::tool
            Graf[Grafana]:::tool
        end

        subgraph Testing [Load Testing Tool local]
            Locust[Locust]:::tool
        end
    end

    UI -->|HTTP :8000| Main
    Locust -->|HTTP :8000| Main
    
    Main -->|Imports| Service
    Service -->|Uses Clients| DB_Mod
    
    DB_Mod -->|TCP :6379| Redis
    
    Prom -.->|Scrapes internal:8000| Main
    Graf -.->|Queries internal:9090| Prom


    DB_Mod ===>|TLS / Internet :27017| Mongo


    linkStyle 7 stroke:red,stroke-width:3px;
```

 2.2 Data Flow: Read (Cache Aside)

 Logic: 
    1. Check Redis Cache (service.py queries REDIS)
    2. Hit: Return Data almost instantly
    3. Miss: We query Mongo, return the data, and the populate Redis Async.

    Write (Write-Through):
 Logic:
    1. Write the data into MongoDb
    2. Populate Redis Async. In this way, Redis won't return outdated data.
























REFERENCES:

[1] https://editor.plantuml.com/uml/LO_1JiCm38RlUGhJ-tW4j8q9L6b84zjEqmvMwhKHIHmbBcX2UtVIBb1wIUBV_sz_MIR1ABspwa4wSWJ1el5A1TGVs19KnqGHQYyKBwWfLV2j04vxYOJE6e5ZVGPC-LAtVwbL2DPe5CF-dW3Gx09xyWBL2oPPxMfOPplvfXe6vBeOJouJF8Rh-Lxb_Pz6qo20kissR50GziBnZ-kT6fFW6NL78zPO3uqtzYrlrgCulcU33cJ9IRp2WTaQtrQ_ABl8ZgIZFXMQruWNz7YUnRUC3GWbcQBPkcNT9ncTnneMYuQ__E9f-AXI-SXAD6qdMHefvrg1L1D0xbcwI9bGE2PnCghxujpgGt4loJUzipy0
[2] 


BIBLIOGRAPHIC INFORMATION:

1. Redis Documentation. (n.d.). Data Types & Pipelining. Retrieved from redis.io.
2. MongoDB Documentation. (n.d.). Aggregation Framework. Retrieved from mongodb.com.
3. FastAPI. High performance Python API. Retrieved from fastapi.tiangolo.com.
4. Prometheus & Grafana. (n.d.). Monitoring Stack. Retrieved from prometheus.io.