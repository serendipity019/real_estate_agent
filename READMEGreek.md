# 🏠 Smart Real Estate Assistant

**Έξυπνος Βοηθός Ακινήτων για την Ελληνική Αγορά**

Μια ολοκληρωμένη εφαρμογή Generative AI που συνδυάζει αναλύσεις αγοράς ακινήτων με υπολογισμούς στεγαστικών δανείων, μέσω φυσικής γλώσσας. Βασίζεται σε FastAPI backend, LangGraph agentic AI, RAG με ChromaDB και Gradio UI.

---

## 📋 Περιγραφή

Ο χρήστης μπορεί να κάνει ερωτήσεις στα ελληνικά ή αγγλικά όπως:

- *"Ποιες είναι οι τιμές ακινήτων στο Κολωνάκι;"*
- *"Υπολόγισέ μου τη μηνιαία δόση για δάνειο 200.000€ με επιτόκιο 3.5% για 20 χρόνια"*
- *"Πόσο κοστίζει ένα σπίτι στη Γλυφάδα και τι δόση θα έχω;"*

Το σύστημα αποφασίζει αυτόματα ποιο εργαλείο να χρησιμοποιήσει (RAG αναζήτηση ή υπολογιστής δανείου) και επιστρέφει μια δομημένη απάντηση.

---

## 🛠️ Τεχνολογίες

| Στρώμα | Τεχνολογία |
|--------|-----------|
| Backend | FastAPI, Python 3.12 |
| AI Agent | LangGraph, LangChain |
| Κύριο LLM | Claude Sonnet 4.6 (Anthropic) |
| Fallback LLM | GPT-4o Mini (OpenAI) |
| Embeddings | OpenAI text-embedding-3-small |
| Vector Store | ChromaDB (persistent) |
| Βάση Δεδομένων | PostgreSQL + SQLModel |
| Authentication | JWT (OAuth2) + Argon2 |
| UI | Gradio 5, mounted στο FastAPI |

---

## ⚙️ Εγκατάσταση

### Προαπαιτούμενα

- Python 3.12+
- PostgreSQL 14+
- Node.js 18+ (μόνο για docx generation scripts)

### Βήματα

```bash
# 1. clone the repository
git clone git@github.com:serendipity019/real_estate_agent.git
cd real_estate_agent

# 2. Δημιουργία virtual environment
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
.venv\Scripts\activate         # Windows

# 3. Εγκατάσταση απαιτούμενων libraries.
pip install -r requirements.txt

# 4. Αντιγραφή και συμπλήρωση μεταβλητών περιβάλλοντος
cp .env.example .env
# Ανοίξε το .env και βάλε τα API keys και τα στοιχεία PostgreSQL

# 5. Δημιουργία βάσης δεδομένων (με Alembic ή απευθείας)
# Εναλλακτικά, το app δημιουργεί τον superuser αυτόματα κατά την εκκίνηση
```

### Μεταβλητές περιβάλλοντος (.env)

```env
# AI Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# PostgreSQL
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=smart_real_estate

# Superuser (δημιουργείται αυτόματα)
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=your_secure_password

# Security
SECRET_KEY=your_secret_key_here
```

---

## 🚀 Εκτέλεση

### Backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Το API είναι διαθέσιμο στο: `http://localhost:8000`
Swagger UI: `http://localhost:8000/docs`

### UI (Gradio)

Το UI είναι mounted απευθείας στο FastAPI — **δεν χρειάζεται ξεχωριστή εκτέλεση**.

Άνοιξε τον browser στο: **`http://localhost:8000/ui`**

### Tests

```bash
pytest tests/ -v
```

---

## 📡 API Endpoints

### Authentication
| Method | Endpoint | Περιγραφή |
|--------|----------|-----------|
| `POST` | `/login/access-token` | Σύνδεση, επιστρέφει JWT token |
| `POST` | `/users/signup` | Εγγραφή νέου χρήστη |
| `POST` | `/reset-password/` | Επαναφορά κωδικού |

### Chat & Sessions
| Method | Endpoint | Περιγραφή |
|--------|----------|-----------|
| `POST` | `/chat` | Αποστολή μηνύματος στον AI agent |
| `POST` | `/sessions/` | Δημιουργία νέας συνομιλίας |
| `GET` | `/sessions/` | Λίστα συνομιλιών χρήστη |
| `GET` | `/sessions/{id}/history` | Ιστορικό συνομιλίας |
| `PATCH` | `/sessions/{id}` | Μετονομασία συνομιλίας |
| `DELETE` | `/sessions/{id}` | Διαγραφή συνομιλίας |

### Knowledge Base (Admin only)
| Method | Endpoint | Περιγραφή |
|--------|----------|-----------|
| `POST` | `/knowledge/ingest` | Εισαγωγή εγγράφου στη γνωσιακή βάση |
| `POST` | `/knowledge/ingest/batch` | Μαζική εισαγωγή εγγράφων |
| `GET` | `/knowledge/stats` | Στατιστικά γνωσιακής βάσης|
| `DELETE` | `/knowledge/reset` | Εκκαθάριση γνωσιακής βάσης|
| `POST` | `/retrieval/query` | Σημασιολογική αναζήτηση |
| `GET` | `/health` | Κατάσταση συστήματος |

---

## 🤖 GenAI Logic

### RAG Pipeline
Έγγραφα αγοράς ακινήτων εισάγονται μέσω `POST /knowledge/ingest`, κόβονται σε chunks (~200 χαρακτήρες με επικάλυψη(overlap).), μετατρέπονται σε embeddings μέσω OpenAI και αποθηκεύονται στο ChromaDB. Κατά την ερώτηση, το σχετικότερο περιεχόμενο ανακτάται και εγχέεται στο prompt.

### AI Agent (LangGraph)
Ο agent χρησιμοποιεί LangGraph `StateGraph` με κύκλο `agent → tools → agent` μέχρι την τελική απάντηση. Αποφασίζει μόνος του αν θα χρησιμοποιήσει:
- `search_knowledge_base` — για ερωτήσεις αγοράς ακινήτων
- `calculate_mortgage` — για υπολογισμούς δανείου

### Fallback
Αν το Claude Sonnet API αποτύχει, ο agent αυτόματα χρησιμοποιεί GPT-4o Mini.

### Conversation Memory
Κάθε `SearchSession` διατηρεί:
- `memory` (JSON cache): γρήγορη φόρτωση για τον agent
- `SearchHistory` (PostgreSQL rows): δόκιμο audit trail ανά turn

---

## 💬 Παραδείγματα Χρήσης

### Παράδειγμα 1 — Ερώτηση αγοράς ακινήτων

**Χρήστης:** `"Ποιες είναι οι τιμές ενοικίασης στο Παγκράτι;"`

**Απάντηση Agent:**
```
Σύμφωνα με την Αναφορά Αγοράς Κέντρου Αθήνας 2026, οι τιμές ενοικίασης
στο Παγκράτι κυμαίνονται μεταξύ 10-12€ ανά τ.μ. για ανακαινισμένα
διαμερίσματα. Υπάρχει υψηλή ζήτηση για διαμερίσματα 50-60 τ.μ. λόγω
φοιτητών και βραχυπρόθεσμων μισθώσεων.

[Εργαλείο που χρησιμοποιήθηκε: search_knowledge_base]
```

---

### Παράδειγμα 2 — Υπολογισμός στεγαστικού δανείου

**Χρήστης:** `"Θέλω να πάρω δάνειο 200.000€ με επιτόκιο 3.5% για 20 χρόνια. Ποιο θα είναι η μηνιαία δόση;"`

**Απάντηση Agent:**
```
Για στεγαστικό δάνειο 200.000€ με επιτόκιο 3.5% και διάρκεια 20 ετών:

• Μηνιαία δόση:        1.159,92 €
• Συνολικό κόστος:     278.380,80 €
• Συνολικοί τόκοι:      78.380,80 €

Ανάλυση αποπληρωμής:
  Έτος 5:   Υπόλοιπο 160.847 € | Πληρωμές: 69.595 €
  Έτος 10:  Υπόλοιπο 114.472 € | Πληρωμές: 139.190 €
  Έτος 15:  Υπόλοιπο  59.350 € | Πληρωμές: 208.786 €
  Έτος 20:  Υπόλοιπο       0 € | Πληρωμές: 278.381 €

[Εργαλείο που χρησιμοποιήθηκε: calculate_mortgage]
```

---

### Παράδειγμα 3 — Συνδυαστική ερώτηση

**Χρήστης:** `"Με ενδιαφέρει ένα σπίτι στα νότια προάστια. Ποιες είναι οι τιμές και αν αγοράσω στα 350.000€ με προκαταβολή 70.000€ και επιτόκιο 4%, ποια θα είναι η μηνιαία δόση μου για 25 χρόνια;"`

**Απάντηση Agent:**
```
Τιμές νοτίων προαστίων (Γλυφάδα, Βούλα):
Οι τιμές πώλησης ξεπερνούν τα 4.500€/τ.μ., καθιστώντας την περιοχή
από τις ακριβότερες στην Αττική.

Υπολογισμός δανείου για ακίνητο 350.000€:
• Κεφάλαιο δανείου:    280.000 € (με προκαταβολή 70.000€)
• Μηνιαίο δόση:        1.476,96 €
• Συνολικό κόστος:     443.088,00 €
• Συνολικοί τόκοι:     163.088,00 €

[Εργαλεία που χρησιμοποιήθηκαν: search_knowledge_base, calculate_mortgage]
```

---

## 📁 Δομή Project

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
│   │       ├── sessions.py      # CRUD για SearchSession
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
│       └── api_client.py        # HTTP client για το API
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

Για πλήρη τεκμηρίωση της αρχιτεκτονικής, των GenAI τεχνικών και των endpoints, δείτε το αρχείο **`[Greek Documentation Smart Real Estate Assistant (PDF)](./docs/Greek_Documentation_Smart_Real_Estate_Assistant.pdf)`** στο repository.

---

## 🔒 Ασφάλεια

- Τα API keys και passwords **δεν ανεβαίνουν ποτέ** στο repository (βλ. `.gitignore`)
- Τα passwords αποθηκεύονται με Argon2 hashing
- Όλα τα endpoints προστατεύονται με JWT Bearer tokens
- Τα admin endpoints (knowledge base, health) απαιτούν `is_superuser=True`
- Τα sessions είναι ιδιωτικά — κάθε χρήστης βλέπει μόνο τα δικά του

---

*Athens University of Economics and Business — AI for Developers Bootcamp. PAPAPANAGIOUTOU PANAGIOTIS*
