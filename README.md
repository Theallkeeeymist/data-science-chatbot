# AI Data Science Interviewer

A full-stack AI-powered mock interview platform built specifically for Data Science roles. The system conducts adaptive technical interviews, evaluates candidate responses using an LLM-based judge, and stores session history per user. It is containerized with Docker and deployable to AWS EC2 via a CI/CD pipeline backed by GitHub Actions and Amazon ECR.

---

## What It Does

The platform simulates a real Data Science interview end to end. A candidate registers, uploads their resume as a PDF, selects the role they are applying for, and begins a live chat-based interview session. The AI interviewer, powered by Meta Llama 3.1 8B via HuggingFace, reads the resume to ask context-relevant questions and dynamically pulls additional technical questions from a Pinecone vector database populated from curated Data Science Q&A sources. Once the interview concludes, a separate judge model evaluates the full transcript and produces a structured report containing a score, verdict, strong areas, weak areas, and improvement suggestions. All interview records are stored per user and are accessible through a profile page.

---

## System Components

### Backend (FastAPI)

The backend is a Python FastAPI application exposing two route groups.

**Authentication Routes** handle user registration, login, and profile management. User credentials are stored in a local SQLite database using SQLAlchemy. Passwords are hashed with SHA-256. Each user record stores their username, hashed password, target role, and resume text so it persists across sessions.

**Interview Routes** manage the lifecycle of an interview session. The `/start` endpoint initializes an `InterviewLoop` object in memory and creates a database record for the session. The `/chat` endpoint processes each candidate turn, injects a RAG-retrieved question as a hidden system message, and returns the model response. The `/feedback` endpoint passes the full session transcript to the `InterviewJudge` and saves the result back to the interview record.

**Bot Logic** (`bot_logic.py`) maintains a running LangChain chat history. At every turn, the RAG engine retrieves a contextually relevant question from Pinecone and injects it as a `SystemMessage` so the LLM can incorporate it naturally into its next question.

**RAG Engine** (`rag_engine.py`) uses `sentence-transformers/all-mpnet-base-v2` embeddings to query a Pinecone vector store. It introduces query variation using random topic suffixes to reduce repetition across sessions.

**Data Ingestion** (`data_ingestion.py`) is a one-time pipeline that scrapes and loads Q&A pairs from HuggingFace datasets, GitHub markdown files, and Analytics Vidhya articles, then upserts them into Pinecone in batches of 100.

**Judge Logic** (`judge_logic.py`) uses a separate LLM call with a structured Pydantic output schema parsed by LangChain's `JsonOutputParser`. It returns verdict, score, summary, strong areas, weak areas, and improvement suggestions.

### Frontend (Streamlit)

The frontend is a multi-page Streamlit application. It walks the user through five views: authentication, resume upload, live interview chat, feedback report, and user profile with interview history. Resume parsing is done client-side using `PyPDFLoader`. A code editor powered by `streamlit-ace` is embedded in the interview view for candidates who want to submit code answers.

### Infrastructure

The project ships with a `docker-compose.yaml` that runs the backend on port 8000 and the frontend on port 8501. A GitHub Actions workflow builds both Docker images, pushes them to Amazon ECR, and deploys to an EC2 instance over SSH on every push to `main`.

---

## Environment Variables

Create a single `.env` file at the root of the project. This file is read by the backend application directly and by Docker Compose when running the containers.

```
PINECONE_API_KEY=your_pinecone_api_key_here
INDEX_NAME=your_pinecone_index_name_here
HUGGINGFACE_HUB_ACCESS_KEY=your_huggingface_access_token_here
HUGGINGFACEHUB_API_TOKEN=your_huggingface_access_token_here
```

| Variable | Description |
|---|---|
| `PINECONE_API_KEY` | API key from your Pinecone project. Found under API Keys in the Pinecone console. |
| `INDEX_NAME` | The name of the Pinecone index where interview Q&A embeddings are stored. Must match the index created during data ingestion. The embedding dimension must be set to 768 to match the `all-mpnet-base-v2` model. |
| `HUGGINGFACE_HUB_ACCESS_KEY` | A HuggingFace User Access Token with read permissions. Required to call `meta-llama/Llama-3.1-8B-Instruct` via the Inference API. Generate one at huggingface.co/settings/tokens. |
| `HUGGINGFACEHUB_API_TOKEN` | The same HuggingFace token as above. This key name is what the HuggingFace client library resolves automatically from the environment when running inside Docker. Set it to the same value as `HUGGINGFACE_HUB_ACCESS_KEY`. |

### GitHub Actions Secrets

The CI/CD pipeline reads these from your repository's GitHub Secrets (Settings > Secrets and variables > Actions).

| Secret Name | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | Access key ID for an IAM user with permissions to push to ECR and describe EC2 instances. |
| `AWS_SECRET_ACCESS_KEY` | The corresponding secret access key for the IAM user above. |
| `EC2_HOST` | The public IP address or DNS hostname of your EC2 instance. |
| `EC2_SSH_KEY` | The private SSH key (PEM format, full contents) used to connect to the EC2 instance. |

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose
- A Pinecone account with a serverless index created in `aws us-east-1`
- A HuggingFace account with access granted to `meta-llama/Llama-3.1-8B-Instruct`

### Clone the Repository

```bash
git clone https://github.com/Theallkeeeymist/data-science-chatbot.git
cd data-science-chatbot
```

### Running Locally Without Docker

**Backend**

```bash
cd backend
python -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Ensure the `.env` file at the project root is present with all four variables listed above, then run the data ingestion pipeline once to populate Pinecone:

```bash
python -c "from chatbot.components.Data_Ingestion.data_ingestion import main; main()"
```

Start the API server:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend**

Open a separate terminal:

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

The frontend will be available at `http://localhost:8501`. It expects the backend at `http://127.0.0.1:8000` by default.

### Running With Docker Compose

Create a `.env` file at the project root containing:

```
HUGGINGFACEHUB_API_TOKEN=your_token_here
```

Then start both services:

```bash
docker compose up -d
```

The backend will be reachable at `http://localhost:8000` and the frontend at `http://localhost:8501`.

### Deploying to EC2

Push to the `main` branch. The GitHub Actions workflow will build both images, push them to ECR, SSH into your EC2 instance, pull the latest images, and restart the containers using `docker compose`. Ensure the EC2 instance already has Docker, Docker Compose, and AWS CLI installed, and that the instance has an IAM role or configured credentials allowing it to pull from ECR.

---

## Project Structure

```
.
├── backend/
│   ├── app.py                          # FastAPI entry point
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── chatbot/
│   │   └── components/
│   │       ├── bot_flow/               # Interview loop and chat logic
│   │       ├── judge/                  # Evaluation and scoring
│   │       ├── rag_implementation/     # Pinecone retrieval engine
│   │       ├── Data_Ingestion/         # One-time data pipeline
│   │       ├── exception/              # Custom exception handling
│   │       └── src_logging/            # File-based logging
│   ├── database/
│   │   ├── database.py                 # SQLAlchemy setup and session
│   │   └── models.py                   # User and Interview ORM models
│   └── routes/
│       ├── auth_routes.py              # Registration, login, profile
│       └── interview_route.py          # Session start, chat, feedback
├── frontend/
│   ├── app.py                          # Streamlit multi-page application
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yaml
└── .github/
    └── workflows/
        └── main.yaml                   # CI/CD pipeline
```
