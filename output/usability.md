# Campus Customs Problem 9 Usability Improvements

## Frontend Improvement 1 — Product Search and Filters

### What was added

The Products page now has an immediate search field, a category filter derived from the catalogue, price sorting in both directions, a reset control, result counts, and a friendly no-results state. Search checks product names, descriptions, tags, colors, and garment types.

### Why it helps

Customers can find relevant merchandise without scrolling through all 102 products. The same controls work on desktop and mobile layouts.

### Files changed

- `frontend/src/App.tsx`
- `frontend/src/styles.css`

### Testing

- The live Products API returned 102 products and 22 categories for the controls.
- The frontend production build passed.
- The filter, sort, reset, and no-results paths are implemented as immediate React state updates without page refreshes.

## Frontend Improvement 2 — Better Chat Experience

### What was added

The chat widget now shows an animated loading indicator, keeps customer and assistant messages visually distinct, scrolls smoothly to the newest message, and shows a retry button when an AI request fails. The existing responsive chat sizing and mobile layout were preserved.

### Why it helps

Customers can tell when the assistant is working, follow longer conversations, and retry a temporary failure without losing the message they attempted to send.

### Files changed

- `frontend/src/App.tsx`
- `frontend/src/styles.css`

### Testing

- The running code contains the loading, automatic-scroll, and retry paths.
- The frontend production build passed.
- The chat endpoint continued returning live responses through the Vite proxy.

## Agent/Backend Improvement 1 — Smart Product Recommendations

### What was added

The `recommend_products` PydanticAI tool accepts product type, minimum/maximum price, size, and result limit preferences. It uses one fresh parameterized SQL query and only returns catalogue products with positive inventory, including the available quantity in its structured result.

### Why it helps

Customers receive useful suggestions based on real preferences without being shown unavailable products or invented merchandise.

### Files changed

- `backend/tools.py`
- `backend/models.py`
- `backend/agent.py`
- `backend/prompts/prompt.md`

### Testing

- `recommend_products(product_type="hoodie", max_price=80, size="M")` returned three real products with positive quantities.
- The live chat request “Recommend hoodies under $80 in size M” returned six real product cards.
- Existing price and stock endpoints still returned the exact Harvard shirt price of `$32.00` and medium quantity of `20`.

## Agent/Backend Improvement 2 — Efficient Database Lookups

### What was added

Search and recommendation operations use parameterized SQL and one SELECT query per tool call. Recommendation availability is checked in the same fresh query rather than through a stale cache or repeated per-product lookup. A targeted `idx_chat_messages_user_id_id` index was added for authenticated history retrieval; the inventory table already had a unique `(product_id, size)` index, so no redundant index was added.

### Why it helps

The agent can respond efficiently while every price and quantity remains a current database read.

### Files changed

- `backend/tools.py`
- `data/campus_customs.db` (added the targeted history index only)

### Testing

- SQLite trace testing recorded one SELECT for `search_products` and one SELECT for `recommend_products`.
- The database still contains 102 catalogue products and 612 inventory records.
- No stock or price cache was introduced.
