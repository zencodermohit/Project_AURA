# 🔮 AI Aura & Personality Reader

> A real-time AI-powered distributed system that analyzes user text input and generates aura/personality interpretations using Kafka event streaming, FastAPI, AI/NLP processing, Docker containers, and a live Streamlit dashboard.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Kafka](https://img.shields.io/badge/Apache_Kafka-4.x-231F20?logo=apachekafka&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.41-FF4B4B?logo=streamlit&logoColor=white)

---

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Aura Types](#-aura-types)
- [Features](#-features)
- [Quick Start](#-quick-start)
- [Manual Setup](#-manual-setup-without-docker)
- [API Documentation](#-api-documentation)
- [How It Works](#-how-it-works)
- [Project Structure](#-project-structure)
- [Screenshots](#-screenshots)
- [Future Improvements](#-future-improvements)
- [Troubleshooting](#-troubleshooting)

---

## 🏗️ Architecture

```
┌─────────────────────┐
│   Streamlit Dashboard │
│   (User Interface)    │
└──────────┬────────────┘
           │ POST /analyze
           ▼
┌─────────────────────┐
│   FastAPI Backend     │
│   (API Service)       │
└──────────┬────────────┘
           │ Produce Event
           ▼
┌─────────────────────┐
│   Apache Kafka        │
│   (Event Streaming)   │
│   Topic: aura-analysis│
└──────────┬────────────┘
           │ Consume Event
           ▼
┌─────────────────────┐
│   Consumer Service    │
│   + AI Aura Engine    │
│   (NLP Processing)    │
└──────────┬────────────┘
           │ Store Result
           ▼
┌─────────────────────┐
│   Results Store       │
│   (In-Memory)         │
└──────────┬────────────┘
           │ GET /results
           ▼
┌─────────────────────┐
│   Dashboard Updates   │
│   (Auto-refresh 3s)   │
└─────────────────────┘
```

The system follows a **distributed event-driven architecture**:

1. **User** enters text into the Streamlit dashboard
2. **Dashboard** sends a POST request to the FastAPI backend
3. **FastAPI** produces an event to the Kafka `aura-analysis` topic
4. **Consumer** receives the event from Kafka
5. **AI Engine** analyzes the text using NLP (sentiment + keyword analysis)
6. **Consumer** stores the result via FastAPI's internal endpoint
7. **Dashboard** polls for results and displays the aura reading

---

## ⚙️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Backend API | FastAPI + Uvicorn | REST API endpoints |
| Event Streaming | Apache Kafka 4.x (KRaft) | Distributed event bus |
| NLP Processing | TextBlob + NLTK + VADER | Sentiment & keyword analysis |
| Dashboard | Streamlit | Real-time visualization |
| Containerization | Docker + Docker Compose | Service orchestration |
| Kafka Client | confluent-kafka ≥2.13.0 | Python Kafka producer/consumer |

---

## ✨ Aura Types

| Aura Type | Color | Energy Level | Key Triggers |
|-----------|-------|-------------|--------------|
| 🟣 **Visionary** | Purple (#9B59B6) | High Creative Energy | dream, future, create, innovate |
| 🔵 **Strategic** | Blue (#3498DB) | Focused Analytical Energy | logic, plan, system, optimize |
| 🟢 **Calm Sage** | Teal (#1ABC9C) | Balanced Harmonious Energy | peace, calm, wisdom, balance |
| 🔴 **Rebel Creator** | Red (#E74C3C) | Intense Disruptive Energy | break, disrupt, bold, defy |
| 🔷 **Analytical Thinker** | Steel Blue (#5DADE2) | Deep Intellectual Energy | analyze, data, research, precise |
| 💚 **Empathic Soul** | Green (#2ECC71) | Warm Nurturing Energy | feel, care, empathy, compassion |
| 🟡 **Ambitious Leader** | Gold (#F39C12) | Powerful Commanding Energy | lead, achieve, power, success |
| 🔹 **Mystic Dreamer** | Cyan (#00BCD4) | Ethereal Cosmic Energy | mystery, cosmic, spiritual, intuition |

---

## 🎯 Features

- **Real-time Event Streaming**: Apache Kafka handles message queuing and async processing
- **NLP-Powered Analysis**: Sentiment analysis (TextBlob + VADER) + keyword-based personality classification
- **Beautiful Dashboard**: Futuristic dark theme with glassmorphism, glow effects, and animations
- **Distributed Architecture**: Decoupled microservices communicating via Kafka
- **Docker Ready**: One-command deployment with Docker Compose
- **Fallback Processing**: Synchronous analysis when Kafka is unavailable
- **Analysis History**: View all past aura readings

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed
- [Docker Compose](https://docs.docker.com/compose/install/) installed

### Launch Everything

```bash
# Clone the repository
cd Project_AURA

# Build and start all services
docker-compose up --build

# Wait for all services to be ready (Kafka takes ~30s)
```

### Access the Application

| Service | URL |
|---------|-----|
| **Dashboard** | http://localhost:8501 |
| **API Docs** | http://localhost:8000/docs |
| **API Health** | http://localhost:8000/ |

### Stop Services

```bash
docker-compose down -v
```

---

## 🔧 Manual Setup (Without Docker)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Download NLTK Data

```bash
python -c "import nltk; nltk.download('punkt_tab'); nltk.download('averaged_perceptron_tagger_eng'); nltk.download('stopwords'); nltk.download('wordnet')"
```

### 3. Start Kafka (using Docker)

```bash
docker run -d --name kafka \
  -p 9092:9092 \
  -e KAFKA_NODE_ID=1 \
  -e KAFKA_PROCESS_ROLES=broker,controller \
  -e KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  -e KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093 \
  -e KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER \
  -e KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT \
  -e KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT \
  -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
  -e KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1 \
  -e KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1 \
  apache/kafka:latest
```

### 4. Start FastAPI

```bash
python main.py
```

### 5. Start Consumer

```bash
python consumer.py
```

### 6. Start Dashboard

```bash
streamlit run dashboard.py
```

---

## 📡 API Documentation

### `GET /`
Health check and service info.

**Response:**
```json
{
  "service": "AI Aura & Personality Reader",
  "status": "online",
  "version": "1.0.0"
}
```

### `POST /analyze`
Submit text for aura analysis.

**Request Body:**
```json
{
  "text": "I love building futuristic systems and having deep conversations.",
  "user_id": "optional-user-id"
}
```

**Response:**
```json
{
  "request_id": "uuid-string",
  "status": "processing",
  "message": "Your aura is being analyzed!"
}
```

### `GET /results`
Get all analysis results.

### `GET /results/{request_id}`
Get a specific analysis result.

**Response:**
```json
{
  "request_id": "uuid-string",
  "aura_type": "Visionary",
  "aura_color": "#9B59B6",
  "energy_level": "High Creative Energy",
  "personality_traits": ["imaginative", "future-focused", "emotionally expressive"],
  "energy_score": 85,
  "confidence_score": 88,
  "sentiment": {"polarity": 0.6, "subjectivity": 0.7, "compound": 0.8},
  "keywords_detected": ["building", "futuristic", "deep"],
  "timestamp": "2026-05-27T11:20:00"
}
```

---

## 🔄 How It Works

### Demonstration Flow

| Step | Action | Component |
|------|--------|-----------|
| 1 | Start all services | `docker-compose up --build` |
| 2 | Open dashboard | Browser → `http://localhost:8501` |
| 3 | Enter personality text | Streamlit text area |
| 4 | Click "Analyze My Aura" | Dashboard → FastAPI |
| 5 | Event streamed to Kafka | FastAPI → Kafka Producer |
| 6 | Consumer processes message | Kafka → Consumer Service |
| 7 | AI predicts aura | Consumer → AI Engine |
| 8 | Dashboard updates instantly | Auto-refresh polling |

### AI Analysis Pipeline

1. **Sentiment Analysis**: TextBlob (polarity/subjectivity) + VADER (compound score)
2. **Tokenization**: NLTK word tokenizer with stopword removal
3. **Lemmatization**: WordNet lemmatizer for keyword normalization
4. **Keyword Matching**: Weighted scoring against 8 aura keyword profiles
5. **Aura Classification**: Highest-scoring aura type selected
6. **Scoring**: Energy score (0-100) + Confidence score (0-100%)

---

## 📁 Project Structure

```
Project_AURA/
├── producer.py              # Kafka producer module
├── consumer.py              # Kafka consumer service (long-running)
├── ai_service.py            # AI/NLP aura analysis engine
├── main.py                  # FastAPI backend API
├── dashboard.py             # Streamlit dashboard UI
├── requirements.txt         # Python dependencies
├── Dockerfile               # Multi-service Docker image
├── docker-compose.yml       # Service orchestration (4 services)
├── .dockerignore             # Docker build exclusions
├── README.md                # This documentation
├── static/
│   └── style.css            # Dashboard custom dark theme
├── templates/               # Reserved for HTML templates
└── screenshots/             # Documentation screenshots
```

---

## 📸 Screenshots

> Screenshots will be added after first deployment.

| Dashboard Input | Aura Result Card | Analysis History |
|:-:|:-:|:-:|
| *Coming soon* | *Coming soon* | *Coming soon* |

---

## 🔮 Future Improvements

- [ ] **WebSocket Live Updates**: Replace polling with real-time push notifications
- [ ] **Database Persistence**: Store results in PostgreSQL/Redis
- [ ] **Webcam Aura Analysis**: Analyze facial expressions via camera
- [ ] **Voice Emotion Analysis**: Detect emotional tone from audio input
- [ ] **User Authentication**: JWT-based login and user profiles
- [ ] **AI-Generated Summary**: LLM-powered personality narrative
- [ ] **Radar Personality Chart**: Visual personality trait breakdown
- [ ] **User History Storage**: Track aura changes over time
- [ ] **Cloud Deployment**: Deploy to AWS/GCP/Azure
- [ ] **Multiple Languages**: Support for non-English text analysis

---

## 🔧 Troubleshooting

### Kafka not starting?
```bash
# Check Kafka logs
docker-compose logs kafka

# Restart Kafka
docker-compose restart kafka
```

### Consumer not connecting?
The consumer retries every 5 seconds for up to 30 attempts. Check logs:
```bash
docker-compose logs consumer
```

### Dashboard not showing results?
1. Verify FastAPI is running: http://localhost:8000/
2. Verify consumer is connected: `docker-compose logs consumer`
3. The dashboard falls back to synchronous processing if Kafka is unavailable

### Port conflicts?
Change the port mappings in `docker-compose.yml`:
```yaml
ports:
  - "YOUR_PORT:8000"  # FastAPI
  - "YOUR_PORT:8501"  # Dashboard
```

---

## 📝 Learning Outcomes

By studying this project, you'll learn:

- ✅ **Distributed System Design** — Event-driven microservices architecture
- ✅ **Apache Kafka** — Event streaming, topics, producers, consumers
- ✅ **FastAPI** — Modern async Python web framework
- ✅ **Docker** — Multi-service containerization with Docker Compose
- ✅ **NLP/AI** — Sentiment analysis, keyword extraction, text classification
- ✅ **Real-time Dashboards** — Streamlit with auto-refresh polling
- ✅ **Service Orchestration** — Health checks, retries, graceful shutdown

---

## 📄 License

This project is for educational purposes. Feel free to modify and distribute.

---

<p align="center">
  <em>Built with ❤️ and 🔮 by Project AURA Team</em>
</p>
