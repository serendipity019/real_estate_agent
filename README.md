Here is the translation of your document into English:

# 🏠 Smart Real Estate Assistant

**Smart Real Estate Assistant for the Greek Market**

---

## 💡 Why I Built This App

The Greek real estate market is one of the most opaque in Europe. Anyone looking to buy, sell, or simply understand the value of a property is faced with a chaos of information: market prices on listing sites, objective values on government maps, bank interest rates in PDFs, Golden Visa legislation in Government Gazettes (ΦΕΚ), and price indices from the Bank of Greece — all scattered across different sources, in different formats, without a single point of reference.

The goal of this application is to solve exactly this problem: to create a **unified digital advisor** that combines all these sources and answers natural language questions — whether you are a buyer wanting to know what an apartment in Pagkrati is worth, an investor calculating loan payments, or a foreigner looking for what changes in the Golden Visa program.

The application is not just a simple chatbot. It is an **Agentic AI** that decides on its own which tools to use for each question — searching the knowledge base, making calculations, querying official government sources, and searching the web for current developments.

---

## 📋 Description

Users can ask questions in Greek or English:

* *"What are the property prices in Kolonaki?"*
* *"Calculate my monthly payment for a loan of €200,000, 3.5%, 20 years"*
* *"What is the objective value for an address in, for example, Zografou?"*
* *"What changes were recently made to the Golden Visa?"*
* *"I have a 57 sq.m. apartment in Pagkrati, 2nd floor — how much can I sell it for?"*

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
| UI | Gradio 5/6, mounted on FastAPI |

---

## ⚙️ Installation

```bash
git clone https://github.com/<your-username>/smart-real-estate-assistant.git
cd smart-real-estate-assistant
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in API keys and DB credentials

```

### Environment Variables (.env)

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=smart_real_estate

FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=your_secure_password
SECRET_KEY=your_secret_key_here

```

---

## 🚀 Execution

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

```

* API + Swagger: `http://localhost:8000/docs`
* Gradio UI: `http://localhost:8000/ui`

The UI is mounted directly on FastAPI — no separate execution is needed.

### Importing data into the knowledge base

```bash
python scripts/ingest_sample_data.py \
  --email admin@example.com \
  --password your_password

```

### Tests

```bash
pytest tests/ -v

```

---

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/login/access-token` | Login, JWT token |
| `POST` | `/users/signup` | User registration |
| `POST` | `/reset-password/` | Password reset |

### Chat & Sessions

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/chat` | Send message to the agent |
| `POST` | `/sessions/` | New conversation |
| `GET` | `/sessions/` | Conversation list |
| `GET` | `/sessions/{id}/history` | Conversation history |
| `PATCH` | `/sessions/{id}` | Rename |
| `DELETE` | `/sessions/{id}` | Delete |

### Knowledge Base & Admin (Superuser only)

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/knowledge/ingest` | Document ingestion |
| `POST` | `/knowledge/ingest/batch` | Batch ingestion |
| `GET` | `/knowledge/stats` | KB statistics |
| `DELETE` | `/knowledge/reset` | Reset KB |
| `GET` | `/health` | System health |

---

## 🤖 AI Agent — 4 Tools

| Tool | Usage |
| --- | --- |
| `search_knowledge_base` | Prices by area, rents, legal framework from ChromaDB |
| `calculate_mortgage` | Monthly payment, interest, amortization schedule |
| `get_objective_zone_price` | Objective value from GSIS/IAPR ArcGIS |
| `search_real_estate_news` | Real-time news search via Tavily |

> ⚠️ **Limitation of `get_objective_zone_price`:** The GSIS API returns HTTP 403 on automated requests (likely requires a browser session token). The agent detects this failure and redirects the user to [maps.gsis.gr/valuemaps](https://maps.gsis.gr/valuemaps/) for manual search.

---

## 🖥️ User Interface

### Chat Tab (all users)

Session sidebar (create/select/rename/delete) + chat panel with server-side conversation memory.

### Admin Tab (superuser only)

Appears automatically if `is_superuser=True`:

* KB Stats: chunks, categories, sources
* Single ingest: text area + source + category dropdown
* Batch file upload: .txt files → documents
* Reset: with "RESET" confirmation

---

## 💬 Usage Examples

### Property Valuation

**User:** `"I have a 57 sq.m. apartment in Pagkrati, 2nd floor. How much can I sell it for?"`

```
Average price Pagkrati: €2,900/sq.m. (Spitogatos Q3 2025)
Estimated value of 57sq.m.: ~€165,300
Realistic range: €145,000 – €185,000
(±15% depending on renovation, elevator, energy class)

```

### Loan Calculation

**User:** `"Loan of €200,000, 3.5%, 20 years"`

```
Monthly payment:  €1,159.92
Total cost:       €278,380.80
Total interest:   €78,380.80

```

### Combined Question

**User:** `"Prices in Glyfada + mortgage loan of €350,000 with a €70,000 down payment, 4%, 25 years"`

```
Glyfada: average price €4,091/sq.m. (+7.15% YoY)
Loan of €280,000: monthly payment €1,476.96

```

---

## 📁 Project Structure

```
sra-phase3/
├── app/
│   ├── main.py                    # FastAPI app + Gradio mount
│   ├── core/                      # config, db, security
│   ├── models/                    # User, SearchSession, SearchHistory
│   ├── schemas/                   # Pydantic DTOs
│   ├── api/routers/               # auth, users, chat, sessions, knowledge...
│   ├── agent/graph.py             # LangGraph StateGraph
│   ├── rag/                       # ChromaDB vector store + pipeline
│   ├── tools/
│   │   ├── mortgage_calculator.py # @tool: annuity formula
│   │   ├── retriever.py           # @tool: RAG search
│   │   ├── gsis_zone_tool.py      # @tool: GSIS objective values
│   │   └── web_search.py          # @tool: Tavily real-time search
│   └── ui/
│       ├── gradio_app.py          # Chat + Admin dashboard
│       └── api_client.py          # HTTP client for the API
├── data/sample_knowledge_base/    # 5 ready-to-use .txt data files
├── scripts/ingest_sample_data.py  # Helper script to functionally import data into the Knowledge Base.
├── tests/                         # 100+ pytest tests
├── requirements.txt
├── .env.example
└── pytest.ini

```

---

## 📄 Documentation

For full documentation of the architecture, GenAI techniques, and endpoints, see the file **[Greek Documentation Smart Real Estate Assistant (PDF)](https://www.google.com/search?q=docs/Greek_Documentation_Smart_Real_Estate_Assistant.pdf)** in the repository.

---

## 🔒 Security

* API keys and passwords **are never uploaded** to the repository (see `.gitignore`)
* Passwords are stored using Argon2 hashing
* All endpoints are protected with JWT Bearer tokens
* Admin endpoints (knowledge base, health) require `is_superuser=True`
* Sessions are private — each user can only see their own

---

*Athens University of Economics and Business — AI for Developers Bootcamp*