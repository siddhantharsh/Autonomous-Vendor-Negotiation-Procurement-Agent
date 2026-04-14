# Autonomous Procurement Agent

A two-phase product intelligence system for IndiaMART. Scrape product listings into a structured vector database, then query them with natural language powered by a local LLM.

---

## How It Works

**Phase 1 — Scrape**
A Streamlit UI lets you paste an IndiaMART category URL and scrape product listings using Selenium (Chrome). Each product is saved as a JSON file containing name, price, supplier, location, GST, specifications, and trust metadata. All files are zipped and uploaded to your Google Drive folder.

**Phase 2 — Query**
The Query Engine tab (or `rag_system.py` CLI) loads the ZIP, embeds every product into a ChromaDB vector store using `sentence-transformers`, and exposes a natural language query interface. Filters for price and location are extracted automatically. If Ollama is running, a Qwen LLM produces a concise AI summary on top of the semantic results.

---

## Project Structure

```
.
├── app.py              — Streamlit frontend (Scraper + Query Engine tabs)
├── scraper.py          — Selenium scraping logic, GDrive upload
├── rag_system.py       — ChromaDB embedding, Ollama integration, query engine
├── gdrive_utils.py     — Google Drive API utilities (auth, upload, download, list)
├── requirement.txt     — Python dependencies
├── .gitignore          — Excludes secrets, drivers, DB, tokens
└── README.md
```

---

## Prerequisites

**Python 3.9+**

**Google Chrome** — must be installed on your system. ChromeDriver is downloaded automatically by `webdriver-manager`.

**Google Cloud Project** — for Google Drive integration:
- Enable the Google Drive API
- Create OAuth 2.0 Desktop credentials
- Download `credentials.json` and place it in the project root

**Ollama** (optional, for AI summaries):
```bash
ollama pull qwen3:0.5b
ollama serve
```

---

## Setup

```bash
git clone https://github.com/Harshitha-katturajan/Procurement-ai-agent-
cd Procurement-ai-agent-

python -m venv venv
source venv/bin/activate

pip install -r requirement.txt
```

Place your `credentials.json` in the project root. On first run, a browser window will open for Google OAuth — `token.json` is then saved automatically.

---

## Usage

### Run the Web App

```bash
streamlit run app.py
```

**Scraper tab** — paste an IndiaMART category URL, set product count, click Start.

**Query Engine tab** — upload a scraped ZIP or load the latest from Google Drive, then query with natural language:
- `Find stainless steel fittings under ₹500 from Mumbai`
- `Suppliers with TrustSEAL verified in Gujarat`
- `Elbow fittings with high ratings`

### CLI Query Engine

```bash
python rag_system.py
```

Prompts for a ZIP path if the database is empty, then starts an interactive query session.

---

## Environment Variables

Create a `.env` file in the project root if needed for future configuration:

```
OLLAMA_MODEL=qwen3:0.5b
OLLAMA_BASE_URL=http://localhost:11434
```

These default values are used even without a `.env` file.

---

## License

MIT License — see `Driver_Notes/LICENSE`.