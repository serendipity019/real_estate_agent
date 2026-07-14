# 🏠 Smart Real Estate Assistant

**Έξυπνος Βοηθός Αγοράς Ακινήτων για την Ελληνική Αγορά**

---

## 💡 Γιατί έφτιαξα αυτή την εφαρμογή

Η ελληνική αγορά ακινήτων είναι από τις πιο αδιαφανείς στην Ευρώπη. Κάποιος που θέλει να αγοράσει, να πουλήσει ή απλώς να κατανοήσει την αξία ενός ακινήτου, βρίσκεται αντιμέτωπος με ένα χάος πληροφοριών: τιμές αγοράς σε sites αγγελιών, αντικειμενικές αξίες σε κυβερνητικούς χάρτες, επιτόκια τραπεζών σε PDF, νομοθεσία για Golden Visa σε ΦΕΚ, και δείκτες τιμών από την Τράπεζα της Ελλάδος — όλα σκόρπια σε διαφορετικές πηγές, σε διαφορετικές μορφές, χωρίς κανένα ενιαίο σημείο αναφοράς.

Ο στόχος αυτής της εφαρμογής είναι να λύσει ακριβώς αυτό το πρόβλημα: να δημιουργήσει έναν **ενιαίο ψηφιακό σύμβουλο** που συνδυάζει όλες αυτές τις πηγές και απαντά σε ερωτήσεις φυσικής γλώσσας — είτε είσαι αγοραστής που θέλεις να ξέρεις τι αξίζει ένα διαμέρισμα στο Παγκράτι, είτε επενδυτής που υπολογίζει δόσεις δανείου, είτε ξένος που ψάχνει τι αλλάζει στο πρόγραμμα Golden Visa.

Η εφαρμογή δεν είναι ένα απλό chatbot. Είναι ένας **Agentic AI** που αποφασίζει ο ίδιος ποια εργαλεία να χρησιμοποιήσει για κάθε ερώτηση — αναζητά στη βάση γνώσης, κάνει υπολογισμούς, ρωτά επίσημες κυβερνητικές πηγές, και ψάχνει στο διαδίκτυο για τρέχουσες εξελίξεις.

---

## 📋 Περιγραφή

Ο χρήστης μπορεί να κάνει ερωτήσεις στα ελληνικά ή αγγλικά:

- *"Ποιες είναι οι τιμές ακινήτων στο Κολωνάκι;"*
- *"Υπολόγισέ μου τη μηνιαία δόση για δάνειο 200.000€, 3.5%, 20 χρόνια"*
- *"Ποια η αντικειμενική αξία για διεύθυνση π.χ στη Ζωγράφου;"*
- *"Τι αλλαγές έγιναν πρόσφατα στο Golden Visa;"*
- *"Έχω διαμέρισμα 57τ.μ. στο Παγκράτι, 2ος όροφος — πόσο μπορώ να το πουλήσω;"*

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
| UI | Gradio 5/6, mounted στο FastAPI |

---

## ⚙️ Εγκατάσταση

```bash
git clone https://github.com/<your-username>/smart-real-estate-assistant.git
cd smart-real-estate-assistant
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # συμπλήρωσε API keys και DB credentials
```

### Μεταβλητές περιβάλλοντος (.env)

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

## 🚀 Εκτέλεση

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API + Swagger: `http://localhost:8000/docs`
- Gradio UI: `http://localhost:8000/ui`

Το UI είναι mounted απευθείας στο FastAPI — δεν χρειάζεται ξεχωριστή εκτέλεση.

### Εισαγωγή δεδομένων στη βάση γνώσης

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
| Method | Endpoint | Περιγραφή |
|--------|----------|-----------|
| `POST` | `/login/access-token` | Σύνδεση, JWT token |
| `POST` | `/users/signup` | Εγγραφή χρήστη |
| `POST` | `/reset-password/` | Επαναφορά κωδικού |

### Chat & Sessions
| Method | Endpoint | Περιγραφή |
|--------|----------|-----------|
| `POST` | `/chat` | Αποστολή μηνύματος στον agent |
| `POST` | `/sessions/` | Νέα συνομιλία |
| `GET` | `/sessions/` | Λίστα συνομιλιών |
| `GET` | `/sessions/{id}/history` | Ιστορικό συνομιλίας |
| `PATCH` | `/sessions/{id}` | Μετονομασία |
| `DELETE` | `/sessions/{id}` | Διαγραφή |

### Knowledge Base & Admin (Superuser only)
| Method | Endpoint | Περιγραφή |
|--------|----------|-----------|
| `POST` | `/knowledge/ingest` | Εισαγωγή εγγράφου |
| `POST` | `/knowledge/ingest/batch` | Μαζική εισαγωγή |
| `GET` | `/knowledge/stats` | Στατιστικά KB |
| `DELETE` | `/knowledge/reset` | Εκκαθάριση KB |
| `GET` | `/health` | Κατάσταση συστήματος |

---

## 🤖 AI Agent — 4 Εργαλεία

| Εργαλείο | Χρήση |
|----------|-------|
| `search_knowledge_base` | Τιμές ανά περιοχή, ενοίκια, νομικό πλαίσιο από ChromaDB |
| `calculate_mortgage` | Μηνιαία δόση, τόκοι, πίνακας αποπληρωμής |
| `get_objective_zone_price` | Αντικειμενική αξία από ΓΓΠΣ/ΑΑΔΕ ArcGIS |
| `search_real_estate_news` | Real-time αναζήτηση νέων μέσω Tavily |

> ⚠️ **Περιορισμός `get_objective_zone_price`:** Το ΓΓΠΣ API επιστρέφει HTTP 403 σε αυτοματοποιημένα αιτήματα (πιθανώς απαιτεί browser session token). Ο agent αναγνωρίζει αυτή την αποτυχία και κατευθύνει τον χρήστη στο [maps.gsis.gr/valuemaps](https://maps.gsis.gr/valuemaps/) για χειροκίνητη αναζήτηση.

---

## 🖥️ User Interface

### Chat Tab (όλοι οι χρήστες)
Session sidebar (δημιουργία/επιλογή/μετονομασία/διαγραφή) + chat panel με server-side conversation memory.

### Admin Tab (μόνο superuser)
Εμφανίζεται αυτόματα αν `is_superuser=True`:
- KB Stats: chunks, κατηγορίες, sources
- Single ingest: text area + source + category dropdown
- Batch file upload: .txt αρχεία → documents
- Reset: με επιβεβαίωση "RESET"

---

## 💬 Παραδείγματα Χρήσης

### Εκτίμηση αξίας ακινήτου

**Χρήστης:** `"Έχω διαμέρισμα 57τ.μ. στο Παγκράτι, 2ος όροφος. Πόσο μπορώ να το πουλήσω;"`

```
Μέση τιμή Παγκράτι: 2.900€/τ.μ. (Spitogatos Q3 2025)
Εκτιμώμενη αξία 57τ.μ.: ~165.300€
Ρεαλιστικό εύρος: 145.000€ – 185.000€
(±15% ανάλογα με ανακαίνιση, ασανσέρ, ενεργειακή κλάση)
```

### Υπολογισμός δανείου

**Χρήστης:** `"Δάνειο 200.000€, 3.5%, 20 χρόνια"`

```
Μηνιαία δόση:    1.159,92€
Συνολικό κόστος: 278.380,80€
Συνολικοί τόκοι:  78.380,80€
```

### Συνδυαστική ερώτηση

**Χρήστης:** `"Τιμές Γλυφάδα + στεγαστικό δάνειο 350.000€ με 70.000€ προκαταβολή, 4%, 25 χρόνια"`

```
Γλυφάδα: μέση τιμή 4.091€/τ.μ. (+7.15% YoY)
Δάνειο 280.000€: μηνιαία δόση 1.476,96€
```

---

## 📁 Δομή Project

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
│   │   ├── gsis_zone_tool.py      # @tool: ΓΓΠΣ αντικειμενικές αξίες
│   │   └── web_search.py          # @tool: Tavily real-time search
│   └── ui/
│       ├── gradio_app.py          # Chat + Admin dashboard
│       └── api_client.py          # HTTP client για το API
├── data/sample_knowledge_base/    # 5 έτοιμα .txt αρχεία δεδομένων
├── scripts/ingest_sample_data.py  # Βοηθητικό script για εισαγωγή δεδομένων στην Βάση γνώσης συναρτησιακά. 
├── tests/                         # 100+ pytest tests
├── requirements.txt
├── .env.example
└── pytest.ini
```

---

## 📄 Documentation

Για πλήρη τεκμηρίωση της αρχιτεκτονικής, των GenAI τεχνικών και των endpoints, δείτε το αρχείο **[Greek Documentation Smart Real Estate Assistant (PDF)](docs/Greek_Documentation_Smart_Real_Estate_Assistant.pdf)** στο repository.

---

## 🔒 Ασφάλεια

- Τα API keys και passwords **δεν ανεβαίνουν ποτέ** στο repository (βλ. `.gitignore`)
- Τα passwords αποθηκεύονται με Argon2 hashing
- Όλα τα endpoints προστατεύονται με JWT Bearer tokens
- Τα admin endpoints (knowledge base, health) απαιτούν `is_superuser=True`
- Τα sessions είναι ιδιωτικά — κάθε χρήστης βλέπει μόνο τα δικά του

---

*Athens University of Economics and Business — AI for Developers Bootcamp*
