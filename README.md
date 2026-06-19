# 🏠 Smart Real Estate Assistant

**Smart Real Estate Assistant for the Greek Market**

A comprehensive Generative AI application that combines real estate market analysis with mortgage calculations via natural language. It is powered by a FastAPI backend, LangGraph agentic AI, RAG with ChromaDB, and a Gradio UI.

---

## 📋 Description

Users can ask questions in Greek or English, such as:

* *"What are the property prices in Kolonaki?"*
* *"Calculate my monthly payment for a €200,000 loan with a 3.5% interest rate for 20 years."*
* *"How much does a house cost in Glyfada and what would my monthly payment be?"*

The system automatically decides which tool to use (RAG search or mortgage calculator) and returns a structured response.

---

## 🛠️ Technologies

| Layer | Technology |
| --- | --- |
| Backend | FastAPI, Python 3.12 |
| AI Agent | LangGraph, LangChain |
| Primary LLM | Claude Sonnet 4.6 (Anthropic) |
| Fallback LLM | GPT-4o Mini (OpenAI) |
| Embeddings | OpenAI text-embedding-3-small |
| Vector Store | ChromaDB (persistent) |
| Database | PostgreSQL + SQLModel |
| Authentication | JWT (OAuth2) + Argon2 |
| UI | Gradio 5, mounted on FastAPI |

---

## ⚙️ Installation

### Prerequisites

* Python 3.12+
* PostgreSQL 14+
* Node.js 18+ (only for docx generation scripts)

### Steps

```bash
# 1. Clone the repository
git clone git@github.com:serendipity019/real_estate_agent.git
cd real_estate_agent

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
.venv\Scripts\activate         # Windows

# 3. Install required libraries
pip install -r requirements.txt

# 4. Copy and fill in environment variables
cp .env.example .env
# Open .env and insert your API keys and PostgreSQL credentials

# 5. Create database (via Alembic or directly)
# Alternatively, the app creates the superuser automatically upon startup

```

### Environment Variables (.env)

```env
# AI Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# PostgreSQL
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=smart_real_estate

# Superuser (created automatically)
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=your_secure_password

# Security
SECRET_KEY=your_secret_key_here

```

---

## 🚀 Execution

### Backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

```

The API is available at: `http://localhost:8000`

Swagger UI: `http://localhost:8000/docs`

### UI (Gradio)

The UI is mounted directly onto FastAPI — **no separate execution is required**.

Open your browser at: **`http://localhost:8000/ui`**

### Tests

```bash
pytest tests/ -v

```

---

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/login/access-token` | Login, returns JWT token |
| `POST` | `/users/signup` | New user registration |
| `POST` | `/reset-password/` | Password reset |

### Chat & Sessions

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/chat` | Send message to the AI agent |
| `POST` | `/sessions/` | Create a new chat session |
| `GET` | `/sessions/` | List user chat sessions |
| `GET` | `/sessions/{id}/history` | Chat session history |
| `PATCH` | `/sessions/{id}` | Rename chat session |
| `DELETE` | `/sessions/{id}` | Delete chat session |

### Knowledge Base (Admin only)

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/knowledge/ingest` | Ingest a document into the knowledge base |
| `POST` | `/knowledge/ingest/batch` | Batch document ingestion |
| `GET` | `/knowledge/stats` | Knowledge base statistics |
| `DELETE` | `/knowledge/reset` | Clear knowledge base |
| `POST` | `/retrieval/query` | Semantic search |
| `GET` | `/health` | System health status |

---

## 🤖 GenAI Logic

### RAG Pipeline

Real estate market documents are ingested via `POST /knowledge/ingest`, split into chunks (~200 characters with overlap), converted to embeddings via OpenAI, and stored in ChromaDB. When a question is asked, the most relevant content is retrieved and injected into the prompt.

### AI Agent (LangGraph)

The agent uses a LangGraph `StateGraph` running an `agent → tools → agent` loop until a final answer is reached. It autonomously decides whether to use:

* `search_knowledge_base` — for real estate market queries
* `calculate_mortgage` — for loan calculations

### Fallback

If the Claude Sonnet API fails, the agent automatically switches to GPT-4o Mini.

### Conversation Memory

Each `SearchSession` maintains:

* `memory` (JSON cache): quick loading for the agent
* `SearchHistory` (PostgreSQL rows): proper audit trail per turn

---

## 💬 Usage Examples

### Example 1 — Real Estate Market Query

**User:** `"What are the rental prices in Pagrati?"`

**Agent Response:**

```
According to the Athens Center Market Report 2026, rental prices
in Pagrati range between €10-12 per sqm for renovated apartments.
There is high demand for 50-60 sqm apartments due to students
and short-term rentals.

[Tool used: search_knowledge_base]

```

---

### Example 2 — Mortgage Calculation

**User:** `"I want to get a loan of €200,000 with a 3.5% interest rate for 20 years. What will the monthly payment be?"`

**Agent Response:**

```
For a mortgage loan of €200,000 with a 3.5% interest rate and a 20-year duration:

• Monthly Payment:     €1,159.92
• Total Cost:          €278,380.80
• Total Interest:      €78,380.80

Repayment Breakdown:
  Year 5:   Remaining Balance €160,847 | Payments: €69,595
  Year 10:  Remaining Balance €114,472 | Payments: €139,190
  Year 15:  Remaining Balance  €59,350 | Payments: €208,786
  Year 20:  Remaining Balance       €0 | Payments: €278,381

[Tool used: calculate_mortgage]

```

---

### Example 3 — Combined Query

**User:** `"I'm interested in a house in the southern suburbs. What are the prices, and if I buy at €350,000 with a €70,000 down payment and a 4% interest rate, what will my monthly payment be for 25 years?"`

**Agent Response:**

```
Southern Suburbs Prices (Glyfada, Voula):
Sales prices exceed €4,500/sqm, making the area one of the most
expensive in Attica.

Loan Calculation for a €350,000 property:
• Loan Capital:        €280,000 (with a €70,000 down payment)
• Monthly Payment:     €1,476.96
• Total Cost:          €443,088.00
• Total Interest:      €163,088.00

[Tools used: search_knowledge_base, calculate_mortgage]

```

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory + Gradio mount
│   ├── core/
│   │   ├── config.py            # Pydantic Settings (.env)
│   │   ├── db.py                # SQLModel engine + init_db
│   │   └── security.py          # JWT + Argon2 password hashing
│   ├── models/                  # SQLModel table=True (DB tables)
│   │   ├── user.py
│   │   ├── search_session.py
│   │   └── history.py
│   ├── schemas/                 # Pydantic DTOs (request/response)
│   │   ├── user.py, chat.py, rag_schemas.py, ...
│   ├── api/
│   │   ├── depedencies.py       # SessionDep, CurrentUser, superuser gate
│   │   └── routers/
│   │       ├── auth.py, users.py, utils.py, private.py
│   │       ├── chat.py          # Session-based chat endpoint
│   │       ├── sessions.py      # CRUD for SearchSession
│   │       ├── health.py, knowledge.py, retrieval.py
│   │       └── __init__.py      # Aggregation (api_router)
│   ├── agent/
│   │   └── graph.py             # LangGraph StateGraph
│   ├── rag/
│   │   ├── vector_store.py      # ChromaDB wrapper
│   │   └── pipeline.py          # Chunking, ingest, retrieve
│   ├── tools/
│   │   ├── mortgage_calculator.py  # @tool: annuity formula
│   │   └── retriever_tool.py       # @tool: RAG search
│   └── ui/
│       ├── gradio_app.py        # Gradio Blocks UI
│       └── api_client.py        # HTTP client for the API
├── tests/                       # 63 tests (pytest)
│   ├── conftest.py              # SQLite fixtures
│   ├── test_auth.py
│   ├── test_sessions.py
│   ├── test_chat.py
│   ├── test_admin_rag_endpoints.py
│   ├── test_mortgage_calculator.py
│   └── test_ui.py
├── data/chroma_db/              # ChromaDB persistent store
├── requirements.txt
├── .env.example
└── pytest.ini

```

---

## 📄 Documentation

Για πλήρη τεκμηρίωση της αρχιτεκτονικής, των GenAI τεχνικών και των endpoints, δείτε το αρχείο **[Greek Documentation Smart Real Estate Assistant (PDF)](./docs/Greek_Documentation_Smart_Real_Estate_Assistant.pdf)** στο repository.

---

## 🔒 Security

* API keys and passwords **are never uploaded** to the repository (see `.gitignore`)
* Passwords are saved using Argon2 hashing
* All endpoints are protected via JWT Bearer tokens
* Admin endpoints (knowledge base, health) require `is_superuser=True`
* Sessions are private — users can only view their own records

---

*Athens University of Economics and Business — AI for Developers Bootcamp. PAPAPANAGIOUTOU PANAGIOTIS*