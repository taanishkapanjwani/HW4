# Campus Customs

Campus Customs is a Yale-inspired collegiate merchandise shop with a React storefront, FastAPI API, and PydanticAI shopping assistant. Customers can browse real catalogue products, view size-level inventory, create accounts, log in, search through chat, and receive database-backed product and stock answers.

## Features and technology

- Responsive Home, Products, About Us, Log In, and Create Account pages
- SQLite-backed product cards, details, prices, images, and inventory
- Account registration, login, logout, PBKDF2 password hashing, and sessions
- PydanticAI chatbot with product search, price, description, stock, size, and recommendation tools
- Dynamic chat product cards, customer memory, safety rules, and audit trail

Built with React, Vite, TypeScript, FastAPI, PydanticAI, Python, and SQLite.

## Local data and configuration

The local data pack must be placed at `data/campus_customs.db` and `data/products/`. These files are intentionally excluded from Git and must be supplied separately.

Copy `.env.example` to `.env` in the project root and set either `PORTKEY_API_KEY` or `OPENAI_API_KEY`. Optional settings are `PORTKEY_BASE_URL`, `PORTKEY_PROVIDER`, and `AI_MODEL` (default `gpt-5.6`). Never commit `.env` or real credentials.

## Installation and running

From the project root:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r requirements.txt
cd frontend
npm install
```

Start the backend from `backend/`:

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

In another terminal, start the frontend:

```bash
cd frontend
npm run dev
```

Open the Vite URL, normally `http://127.0.0.1:5173`.

## Testing

Browse `/products`, open a product card, and verify the real description, price, image, and size stock. Create an account, log out, and log in again to test authentication. In the chatbot, try `What is the price of Basic Hoodie Big Yale and how many medium are in stock?` and `What hoodies do you have?`. The Products page also supports keyword search, category filtering, and price sorting.

Production/build checks:

```bash
cd frontend && npm run build
cd .. && backend/.venv/bin/python -m py_compile backend/*.py
```

## Documentation and submission files

- `AI_prompts.md` records the prompts for Problems 1–13.
- `output/harness.md` documents the database, authentication, agent, models, tools, memory, safety, audit, limits, and commands.
- `output/design.md` and `output/usability.md` document Problems 10 and 9.
- `output/app_check.html` is the standalone Problem 11 report.
- `output/app_check_images/` is the testing screenshot location; browser screenshots were environment-limited during automated checking.
- `output/audit_trail.json` contains non-sensitive agent/tool activity records.

## Public repository safety

Before publishing, inspect Git status and staging. `.gitignore` excludes `.env`, API-key files, databases, product images, `node_modules`, Python environments, caches, build output, and temporary files. The local data pack is required at runtime but must not be committed to a public repository.
