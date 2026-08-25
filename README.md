# DealX-AI

DealX-AI is an AI shopping assistant that identifies products by barcode and provides product summaries and review-based answers. It combines a React/Vite frontend, a FastAPI backend, local product data, external product lookup, and a Chroma vector store containing review embeddings.

## Features

- Search for products by entering a barcode.
- Scan a barcode with a device camera.
- Resolve products from the local database or an external product API.
- Generate an AI shopping summary.
- Ask questions about a product using retrieved review context.
- Fall back to product information for products found through the external API.

## Project Structure

```text
DealX-AI/
|-- backend/
|   |-- main.py                 FastAPI application and API routes
|   |-- api/product_api.py      External product lookup
|   |-- data/products.json      Local product catalog
|   `-- rag/rag_pipeline.py     Embeddings, retrieval, and Groq prompts
|-- chroma_db/                  Persisted Chroma vector store
|-- frontend/
|   |-- src/App.jsx             React application
|   `-- package.json             Frontend scripts and dependencies
`-- archive/                     Older data and RAG scripts
```

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer
- npm
- A Groq API key
- A browser with camera access if barcode scanning is used

## Setup

### 1. Configure the backend

From the repository root, create `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key
```

Create and activate a Python virtual environment, then install the backend dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn pydantic python-dotenv groq requests chromadb langchain-chroma langchain-huggingface sentence-transformers
```

The first startup may download the Hugging Face embedding model `sentence-transformers/all-MiniLM-L6-v2`.

### 2. Install the frontend

```powershell
cd frontend
npm install
```

## Run the Application

Start the backend from the repository root:

```powershell
uvicorn backend.main:app --reload --host 0.0.0.0
```

In a second terminal, start the frontend:

```powershell
cd frontend
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://localhost:5173`.

For a phone, open the network URL printed by Vite, such as
`http://192.168.1.20:5173`, while the phone and computer are on the same
network. The backend listens on the LAN because the frontend uses the same
hostname for API requests.

Camera access on phones requires a secure context. Use `localhost` for local
desktop testing, or serve the Vite app over HTTPS when testing from a phone.

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | Backend health check |
| `GET` | `/products` | Return all local products |
| `GET` | `/product/barcode/{barcode}` | Find a product by barcode |
| `GET` | `/product/{product_id}/summary` | Generate an AI product summary |
| `POST` | `/ask` | Ask about a local product using its product ID |
| `POST` | `/ask/barcode` | Ask about a product using its barcode |

Interactive API documentation is available at `http://127.0.0.1:8000/docs` while the backend is running.

### Example requests

Find the sample local product:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/product/barcode/8901234567890
```

### Barcode testing

## 🧪 Testing

DealX-AI includes 25 demo products with locally defined barcodes.

| Product | Barcode |
|---|---|
| SoundMax Pro Wireless Headphones | `8901234567890` |
| AudioBeat ANC Wireless Headphones | `8901234567891` |
| TypePro Mechanical Keyboard | `8901234567895` |
| SwiftClick Wireless Mouse | `8901234567899` |
| NovaOne 5G Smartphone | `8901234567903` |
| BoomBox Mini Bluetooth Speaker | `8901234567908` |
| FitPulse Active Smartwatch | `8901234567912` |

### Test

Enter any barcode above in the application to retrieve the product.

You can then ask the AI assistant questions about the product, compare
products, or request recommendations.

> **Note:** These are demo/local barcodes created for testing purposes.

For example, test a known barcode from PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/product/barcode/8901234567895
```

Ask a question about a local product:

```powershell
$body = @{ product_id = "P001"; question = "What are the main pros and cons?" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/ask -ContentType "application/json" -Body $body
```

## Frontend Commands

Run these commands from `frontend/`:

```powershell
npm run dev       # Start the development server
npm run build     # Create a production build
npm run lint      # Run ESLint
npm run preview   # Preview the production build
```

## Notes

- Local products are loaded from `backend/data/products.json`.
- Review-based answers depend on matching documents in the existing `chroma_db` store.
- External product lookup requires network access and may return no result for an unknown barcode.
- Camera scanning requires browser permission and works best over a secure context or localhost.
- Do not commit `backend/.env` or expose the Groq API key in frontend code.
