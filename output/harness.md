# Campus Customs Database Harness

This document records the current database structure for the Campus Customs website and chatbot. It is based only on the schema that exists in `data/campus_customs.db`.

## Database tables

The database contains these tables:

1. `catalogue` — the product catalogue.
2. `inventory` — available quantities for each product and size.
3. `users` — customer account information.
4. `chat_messages` — chatbot conversation history and product matches.
5. `sqlite_sequence` — an internal SQLite table that tracks the next values for auto-incrementing integer keys.

## Table details

### `catalogue`

| Field | SQLite type | Key/constraint | Purpose |
|---|---|---|---|
| `product_id` | `TEXT` | Primary key | Uniquely identifies a product and connects it to its inventory records. |
| `name` | `TEXT` | Required | Product name shown in the shop and used in chatbot responses. |
| `garment_type` | `TEXT` | Required | Identifies the kind of merchandise, such as a hoodie or shirt, for display and filtering. |
| `description` | `TEXT` | Required | Product details that can be shown to customers or used by the chatbot. |
| `colors` | `TEXT` | Required | Stores the product's color information for display and product matching. |
| `search_tags` | `TEXT` | Required | Search terms that help the website and chatbot find relevant products. |
| `image_file_path` | `TEXT` | Required | Location of the product image used in the product listing or recommendation. |
| `price` | `REAL` | Required | Product price displayed to customers and reported by the chatbot. |

### `inventory`

| Field | SQLite type | Key/constraint | Purpose |
|---|---|---|---|
| `id` | `INTEGER` | Primary key; auto-incrementing | Uniquely identifies an inventory record. |
| `product_id` | `TEXT` | Required; foreign key to `catalogue.product_id` | Identifies which catalogue product the stock belongs to. |
| `size` | `TEXT` | Required | Identifies the size whose stock is being recorded. |
| `quantity` | `INTEGER` | Required | Number of units available for the product and size, used for stock checks. |

There is also a unique constraint on the combination of `product_id` and `size`, so a product-size pair can have only one inventory record.

### `users`

| Field | SQLite type | Key/constraint | Purpose |
|---|---|---|---|
| `id` | `INTEGER` | Primary key; auto-incrementing | Uniquely identifies a customer account and connects the customer to chat messages. |
| `name` | `TEXT` | Required | Stores the account name for customer identification or display. |
| `email` | `TEXT` | Required; unique | Stores the customer's login/contact email and prevents duplicate accounts. |
| `password_hash` | `TEXT` | Required | Stores the password securely as a hash for authentication; it is not the plain-text password. |
| `created_at` | `TEXT` | Required; defaults to `datetime('now')` | Records when the customer account was created. |
| `first_name` | `TEXT` | Optional | Stores the customer's first name when provided. |
| `last_name` | `TEXT` | Optional | Stores the customer's last name when provided. |

### `chat_messages`

| Field | SQLite type | Key/constraint | Purpose |
|---|---|---|---|
| `id` | `INTEGER` | Primary key; auto-incrementing | Uniquely identifies a saved chat message. |
| `user_id` | `INTEGER` | Required; foreign key to `users.id` | Identifies the customer whose conversation contains the message. |
| `role` | `TEXT` | Required | Identifies the message role, such as a customer or assistant message. |
| `content` | `TEXT` | Required | Stores the text of the customer's question or chatbot response. |
| `products_json` | `TEXT` | Optional | Stores product-match information associated with a chatbot message. |
| `created_at` | `TEXT` | Required; defaults to `datetime('now')` | Records when the message was created. |

### `sqlite_sequence`

This is an internal SQLite table created for tables using `AUTOINCREMENT`. It contains the following fields:

| Field | SQLite type | Purpose |
|---|---|---|
| `name` | Not declared | Stores the name of an auto-incrementing table. |
| `seq` | Not declared | Stores the most recent generated integer value for that table. |

The application should not use this table for normal shopping, account, inventory, or chatbot operations.

## Table connections

```text
catalogue.product_id 1 ─── many inventory.product_id
users.id              1 ─── many chat_messages.user_id
```

- `catalogue.product_id` is the primary key referenced by `inventory.product_id`.
- `inventory.product_id` is required, and each product-size combination is unique.
- `users.id` is the primary key referenced by `chat_messages.user_id`.
- `chat_messages.user_id` is required, so each saved chat message belongs to a user.
- No other foreign-key relationships are defined in the existing schema.

## Website and chatbot use

- Product pages and listings use `catalogue` for names, descriptions, images, colors, tags, and prices.
- Stock checks join `catalogue` to `inventory` using `product_id` and filter by `size`.
- Search and chatbot matching can use `name`, `garment_type`, `description`, `colors`, and `search_tags`.
- Customer account features use `users`.
- Conversation history and returned product matches use `chat_messages`.
- The chatbot must read the current `price` and `quantity` values from the database when answering price and stock questions.

## Future harness sections

The following sections are reserved for later problems:

- AI models
- Tools and database access
- Safety rules
- Application specifications

## Problem 3 architecture

### Frontend

- `frontend/` contains the React, Vite, and TypeScript client.
- React Router provides routes for Home, Products, individual products, About Us, Log In, and Create Account.
- The Products page calls `GET /api/products` and renders the returned catalogue records.
- A product card links to `/products/{product_id}`, which calls `GET /api/products/{product_id}` for inventory by size.
- Images use the database's `image_file_path` through the backend's `/images/` static route.
- The floating chatbot is currently a local UI placeholder; it does not call an AI model.

### Backend

- `backend/main.py` contains the read-only FastAPI application.
- `GET /api/health` checks that the service is running.
- `GET /api/products` returns catalogue data ordered by product name.
- `GET /api/products/{product_id}` returns one catalogue record plus its inventory records.
- `/images/` serves the existing files under `data/` so product paths remain database-driven.
- The backend uses parameterized SQLite queries and does not write to the database.

### Current placeholders and future work

- Login and Create Account forms validate browser input but do not authenticate or write users.
- The chat panel accepts messages locally but is not connected to PydanticAI.
- Shopping bag, checkout, and ordering are not implemented.
- AI model configuration, tools, safety rules, and authentication details should be added in later problems.

## Problem 4 authentication

### Registration

- The Create Account form collects `first_name`, `last_name`, `email`, `password`, and `confirm_password`.
- Browser validation checks required fields, email format, password length, and matching passwords.
- `POST /api/auth/register` validates the request again on the backend, normalizes the email to lowercase, and inserts the new user into `users`.
- The existing `name` column is populated with the combined first and last name; the separate `first_name` and `last_name` columns are also populated.
- Duplicate email addresses return a friendly conflict error and do not create another row.

### Login and logout

- `POST /api/auth/login` looks up the email and verifies the submitted password against the stored hash.
- Incorrect or unknown credentials return HTTP 401 without revealing whether an email exists.
- Successful registration and login set an opaque, random, HttpOnly, SameSite cookie named `campus_customs_session`.
- The server keeps the session token mapped to the user ID and exposes only public user fields through `/api/auth/me`.
- `POST /api/auth/logout` removes the session and clears the cookie.
- The frontend shows success/error feedback and displays a logout control for the current user.

### Password protection

- The existing database uses the format `pbkdf2_sha256$<salt>$<digest>` with 120,000 PBKDF2-HMAC-SHA256 iterations.
- New passwords use the same format with a fresh random salt for every account.
- Plain-text passwords are never inserted into SQLite, returned by an endpoint, or sent back to the frontend.
- The API response models and `/api/auth/me` response contain no `password_hash` field.

### Problem 4 verification

- Existing user `test@campuscustoms.yale.edu` with the supplied password: login succeeded.
- Incorrect password: rejected with HTTP 401.
- Separate test account `problem4.test.20261007@campuscustoms.yale.edu`: inserted as user ID 4 and login succeeded after logout.
- Duplicate registration for that email: rejected with HTTP 409.
- SQLite verification showed the new row uses the `pbkdf2_sha256` algorithm and a 95-character hash value.
- Existing users were preserved; no rows were overwritten or deleted.

## Problem 5 PydanticAI agent architecture

### Request flow

```text
React chat widget
    → POST /api/chat { message }
    → FastAPI validates ChatRequest
    → PydanticAI agent loads prompt.md and calls the configured model
    → FastAPI returns ChatResponse { reply, products }
    → React renders the reply in the chat panel
```

- `frontend/src/api.ts` sends chat messages to `/api/chat` through the Vite development proxy.
- `frontend/src/App.tsx` shows the assistant reply, a loading state, and a useful error when the request fails.
- `backend/main.py` preserves the product and authentication endpoints and adds the chat endpoint.

### Required agent files

- `backend/prompts/prompt.md` contains the assistant personality, shopping scope, and rules against inventing facts or exposing secrets.
- `backend/agent.py` reads that file at startup, selects an OpenAI-compatible model, configures Portkey or OpenAI from environment variables, and runs the PydanticAI agent.
- `backend/tools.py` is the extension point for future database-backed product and inventory tools. It currently registers no tools, so the agent cannot fabricate database facts.
- `backend/models.py` defines `ChatRequest`, `ChatResponse`, and `ProductCard` for structured chat data.

### Model and secrets

- `PORTKEY_API_KEY` is preferred when present; `PORTKEY_BASE_URL`, `PORTKEY_PROVIDER`, and `AI_MODEL` can customize the connection.
- `OPENAI_API_KEY` is supported as a fallback.
- The default model setting is `gpt-5.6`, and it can be overridden through `AI_MODEL` without changing source code.
- `.env` is loaded for local development, but secrets are never returned to the frontend or committed to Git.
- If no model key is configured, `/api/chat` returns a clear HTTP 503 configuration error rather than a fake response.

### Problem 5 limitation

The agent was initially connected without database tools; Problem 6 adds read-only product and inventory tools. Recommendations and store policies remain outside the current tool scope.

## Problem 6 database tools

All tools in `backend/tools.py` open the existing SQLite database read-only and use `?` parameters for user-supplied product and size values. Product names, prices, quantities, and sizes are never hardcoded.

| Tool | Result model | Purpose |
|---|---|---|
| `list_products` | `ProductListResult` with `count` and `products` | Returns the actual catalogue for broad questions such as what the shop sells. |
| `lookup_product` | `ProductInfoResult` | Returns product ID, name, garment type, description, colors, price, and all listed size quantities. |
| `get_product_price` | `StockResult` | Returns the exact `catalogue.price` for a matching product. |
| `get_product_stock` | `StockResult` | Sums `inventory.quantity` across all sizes for a matching product. |
| `get_size_stock` | `StockResult` | Returns the exact quantity for a product-size pair and distinguishes an unlisted size from zero stock. |

### Tool result fields

- `ProductSummary` uses `product_id`, `name`, `garment_type`, and `price` for compact catalogue results.
- `ProductInfoResult` uses the catalogue's descriptive fields plus a `sizes` list so the assistant can describe a product without guessing.
- `SizeStock` uses `size`, `quantity`, and `available` for each inventory record.
- `StockResult` uses `product_id`, `name`, `size`, `size_listed`, `quantity`, and `available` so missing products, missing sizes, in-stock sizes, and zero-stock sizes are all distinguishable.
- `found` and `message` provide explicit outcomes when no product matches or a size is not listed.

### Accuracy behavior

The agent registers all five tools through `DATABASE_TOOLS` in `backend/agent.py`. The system prompt requires tool calls for product descriptions, prices, and stock. If a tool returns `found: false`, `size_listed: false`, or `quantity: 0`, the assistant must communicate that result rather than inventing a value. No database writes occur in these tools.

## Problem 7 chat search and dynamic cards

### Search flow

```text
Customer asks for a category
    → PydanticAI calls search_products(query)
    → SQLite searches catalogue fields with parameterized SQL
    → ProductSearchResult is captured from the agent tool return
    → POST /api/chat returns { reply, products }
    → React adds an assistant message and renders product cards
```

- `search_products` searches `name`, `garment_type`, `description`, `colors`, and `search_tags` from `catalogue`.
- It handles common plural category terms while retaining only database rows that match the supplied search terms.
- Each result is a `ProductSearchCard` containing `product_id`, `name`, `price`, `description`, and an `/images/` URL derived from `image_file_path`.
- A no-match search returns an empty `products` list and a clear message; unrelated products are not shown.

### API and frontend behavior

- `ChatResponse.products` now contains `ProductSearchCard` objects alongside the conversational `reply`.
- `frontend/src/api.ts` returns both fields from `/api/chat`.
- The floating chat widget renders returned products inside the assistant message as responsive cards with the actual image, name, description, and price.
- Each card is a React Router link to `/products/{product_id}`, preserving the existing product detail page and its database-backed description, price, and inventory.
- New searches append a new assistant result, so a category search visibly updates the conversation with the latest matching cards.

## Problem 8 customer memory and page context

### Chat history storage and retrieval

- The existing `chat_messages` table is used; no redundant table was created. It stores `user_id`, `role`, `content`, `products_json`, and its database timestamp.
- `POST /api/chat` saves both the authenticated customer's message and the assistant response. Search product cards are preserved in `products_json`.
- `GET /api/chat/history` requires the authenticated session cookie and queries only rows where `user_id` equals the session's user ID, returning the most recent 20 messages in chronological order.
- The React chat widget requests history after login and on route changes. Logout clears the in-memory widget conversation before another user's context can load.
- Guests can use `POST /api/chat`, but their messages are not inserted into `chat_messages`; guest history requests return HTTP 401.

### Trusted customer and page dependencies

- `AgentDeps` in `backend/agent.py` carries a `CustomerContext`, verified page context, and recent conversation messages into each PydanticAI run.
- The customer context contains only `id`, `first_name`, `last_name`, and `email` from the authenticated `users` record. Passwords and hashes are never included.
- The frontend sends only the current product ID in `page_context`. FastAPI resolves that ID through the existing database lookup tool and passes the verified name, description, price, colors, and sizes to the agent.
- The agent instructions explicitly identify the current product ID for phrases such as “this product,” then require the existing database tools for price, stock, size, and description answers.
- Navigation updates the product ID sent with the next message, preventing the previous product from being reused.

### Privacy behavior

- Chat history is never selected by a user-supplied user ID; it is scoped to the server-side authenticated session.
- Returning users receive their own history only. A second verified test account received zero messages and could not see the first account's marker.

## Problem 9 usability and performance

- The Products page filters the API catalogue client-side by keyword/category and sorts by price without a refresh. It includes a reset action and a no-results state.
- The chat widget shows a loading state, distinct user/assistant bubbles, automatic scrolling, and a retry action after a failed request.
- `recommend_products` filters real catalogue rows by product type, optional price bounds, and optional in-stock size. It caps its requested result limit to 12 and checks positive inventory in SQL.
- Product search uses one parameterized catalogue query per call. Recommendation uses one parameterized query with an inventory `EXISTS` condition and a fresh stock quantity calculation; stock and prices are not cached.
- The Problem 9 database index is `idx_chat_messages_user_id_id`, used to support user-scoped recent history lookups.

## Problem 12 audit trail and safety

### Audit trail

- `backend/audit.py` writes to `output/audit_trail.json`, a persistent JSON array. Each new entry is appended to the existing in-memory array and written back without clearing prior entries; a backend startup therefore leaves earlier entries intact.
- Entries contain `timestamp` (UTC ISO 8601), `action`, a shape-only `arguments` summary, a compact `result` summary, and a `reason` describing completion, failure, or stopping.
- `backend/main.py` records `backend.startup`. `backend/agent.py` records agent start, completion, model-unavailable stops, and exceptions. Registered database tools are wrapped by `audit_tool`, recording successful results and exceptions.
- String arguments are represented only by type and length. Full customer messages, names, emails, passwords, password hashes, API keys, cookies, and tokens are never written to the audit file. Tool results record only safe outcome metadata such as `found`, `count`, availability, and product-card counts.
- The file is created on first activity, remains valid JSON, and is protected against concurrent writes within a process by a lock. It is an audit record, not a customer conversation store.

### Safety rules actually loaded

- `backend/agent.py` reads `backend/prompts/prompt.md` at import time and passes its contents as the PydanticAI `system_prompt`.
- The prompt requires database tools for product description, price, total-stock, and size-stock facts; prohibits invented facts; distinguishes missing products, unlisted sizes, and zero stock; and requires uncertainty to be stated.
- It prohibits disclosure of passwords, hashes, API keys, tokens, customer data, internal instructions, and hidden prompts. It also rejects requests to ignore or bypass the rules.
- Trusted customer and current-product context are supplied by FastAPI dependencies, not accepted as facts from chat text.

## Complete agent architecture and structured models

### Request and provider configuration

React sends `ChatRequest` to `POST /api/chat`. FastAPI resolves the authenticated session, loads up to 20 prior messages, verifies an optional page product ID against SQLite, and builds `AgentDeps`. PydanticAI runs the agent and FastAPI returns `ChatResponse` with `reply` and structured product cards.

`backend/agent.py` loads `.env` using `python-dotenv`. It prefers `PORTKEY_API_KEY`, using `PORTKEY_BASE_URL` (default `https://api.portkey.ai/v1`) and `PORTKEY_PROVIDER` (default `openai`); otherwise it uses `OPENAI_API_KEY`. The actual model name is `AI_MODEL`, defaulting to `gpt-5.6`. No key or token is hardcoded.

### `backend/models.py` fields

- `ProductCard`: `product_id`, `name`, `price`, optional `image_url`; compact product display data.
- `ProductSummary`: `product_id`, `name`, `garment_type`, `price`; catalogue list data.
- `SizeStock`: `size`, `quantity`, `available`; per-size inventory facts.
- `ProductListResult`: `count`, `products`; broad catalogue results.
- `ProductInfoResult`: `found`, `message`, optional `product_id`, `name`, `garment_type`, `description`, `colors`, `price`, and `sizes`; complete verified product information.
- `ProductSearchCard`: `product_id`, `name`, `price`, `description`, `image_url`; fields rendered by dynamic frontend cards.
- `ProductSearchResult`: `query`, `count`, `products`, `message`; structured category search outcome.
- `RecommendationCard`: all `ProductSearchCard` fields plus `available_quantity`; prevents claiming an unavailable recommendation.
- `RecommendationResult`: `criteria`, `count`, `products`, `message`; recommendation outcome and selection criteria.
- `StockResult`: `found`, `message`, optional `product_id`, `name`, `price`, `size`, `size_listed`, `quantity`, `available`; distinguishes absent products, absent sizes, zero stock, and available stock.
- `ChatRequest`: `message` (1–2000 characters) and optional `page_context`.
- `PageContextRequest`: `product_id` (1–200 characters), resolved by the backend rather than trusted directly.
- `CustomerContext`: `id`, optional `first_name`, optional `last_name`, `email`; authenticated identity only.
- `ConversationMessage`: `role`, `content`, optional `created_at`, and optional matching product cards.
- `ChatHistoryResponse`: `messages`; authenticated user's restored conversation.
- `VerifiedPageContext`: verified product ID, name, description, price, colors, and size stock.
- `ChatResponse`: `reply` and dynamic `products` returned to React.

### Tools and limits

The registered tools are `list_products`, `search_products`, `lookup_product`, `get_product_price`, `get_product_stock`, `get_size_stock`, and `recommend_products`. All use parameterized SQLite queries. Search returns every matching catalogue row; there is no separate search-result cap in the current implementation. Recommendations default to 6 and clamp the requested limit to 1–12. Chat messages are capped at 2,000 characters and restored history is capped at 20 messages. No explicit PydanticAI agent loop/step limit is configured in source, so the library default applies. The source does not configure a request timeout or response-token limit.

## Running instructions

From the project root, install backend dependencies with:

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Create a root `.env` file with `PORTKEY_API_KEY` (and optionally `PORTKEY_BASE_URL`, `PORTKEY_PROVIDER`, and `AI_MODEL`) or use `OPENAI_API_KEY`. Keep `.env` out of Git.

Start the backend from the `backend` folder exactly with:

```bash
uvicorn main:app --reload --port 8000
```

In a second terminal, start the React/Vite frontend:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at the Vite URL, normally `http://127.0.0.1:5173`, and proxies `/api` and `/images` to the backend according to its Vite configuration. The database at `data/campus_customs.db`, product files under `data/products/`, and secrets are runtime inputs and must not be committed.
- Guest conversations remain available in the current browser session but are not permanently stored.
