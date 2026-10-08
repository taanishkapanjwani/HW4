"""Read-only, parameterized database tools for the Campus Customs agent."""

from pathlib import Path
import sqlite3
import re
from typing import List, Optional
try:
    from .audit import audit_tool
except ImportError:
    from audit import audit_tool

try:
    from .models import ProductInfoResult, ProductListResult, ProductSearchCard, ProductSearchResult, ProductSummary, RecommendationCard, RecommendationResult, SizeStock, StockResult
except ImportError:  # Supports `uvicorn main:app` from the backend directory.
    from models import ProductInfoResult, ProductListResult, ProductSearchCard, ProductSearchResult, ProductSummary, RecommendationCard, RecommendationResult, SizeStock, StockResult


DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "campus_customs.db"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _find_product(connection: sqlite3.Connection, query: str) -> Optional[sqlite3.Row]:
    """Resolve an exact product ID/name first, then a case-insensitive name search."""
    cleaned = query.strip()
    return connection.execute(
        """SELECT product_id, name, garment_type, description, colors,
                  search_tags, image_file_path, price
           FROM catalogue
           WHERE product_id = ? OR lower(name) = lower(?)
              OR lower(name) LIKE lower(?)
           ORDER BY CASE WHEN product_id = ? THEN 0
                         WHEN lower(name) = lower(?) THEN 1 ELSE 2 END, name
           LIMIT 1""",
        (cleaned, cleaned, "%" + cleaned + "%", cleaned, cleaned),
    ).fetchone()


def list_products() -> ProductListResult:
    """List the actual products in the catalogue for broad shopping questions."""
    with _connection() as connection:
        rows = connection.execute(
            "SELECT product_id, name, garment_type, price FROM catalogue ORDER BY name"
        ).fetchall()
    return ProductListResult(
        count=len(rows),
        products=[
            ProductSummary(product_id=row["product_id"], name=row["name"], garment_type=row["garment_type"], price=row["price"])
            for row in rows
        ],
    )


def search_products(query: str) -> ProductSearchResult:
    """Search actual catalogue names, categories, descriptions, colors, and tags for matching products."""
    stop_words = {"a", "an", "any", "do", "have", "me", "of", "products", "product", "show", "the", "what", "you"}
    raw_terms = re.findall(r"[a-z0-9-]+", query.lower())
    terms = [term for term in raw_terms if term not in stop_words]
    if not terms:
        return ProductSearchResult(query=query, count=0, message="No searchable product category was provided.")

    clauses = []
    parameters: List[str] = []
    for term in terms:
        variants = [term]
        if len(term) > 3 and term.endswith("s"):
            variants.append(term[:-1])
        variant_clauses = []
        for variant in variants:
            pattern = "%" + variant + "%"
            variant_clauses.append("(lower(name) LIKE ? OR lower(garment_type) LIKE ? OR lower(description) LIKE ? OR lower(colors) LIKE ? OR lower(search_tags) LIKE ?)")
            parameters.extend([pattern] * 5)
        clauses.append("(" + " OR ".join(variant_clauses) + ")")

    with _connection() as connection:
        rows = connection.execute(
            """SELECT product_id, name, price, description, image_file_path
               FROM catalogue WHERE """ + " AND ".join(clauses) + " ORDER BY name",
            parameters,
        ).fetchall()
    products = [
        ProductSearchCard(
            product_id=row["product_id"], name=row["name"], price=row["price"],
            description=row["description"], image_url="/images/" + row["image_file_path"].lstrip("/"),
        )
        for row in rows
    ]
    return ProductSearchResult(
        query=query, count=len(products), products=products,
        message="Matching products found." if products else "No matching products were found.",
    )


def lookup_product(query: str) -> ProductInfoResult:
    """Look up a catalogue product by product ID or a name/search phrase."""
    with _connection() as connection:
        row = _find_product(connection, query)
        if row is None:
            return ProductInfoResult(found=False, message="No matching product was found.")
        inventory = connection.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY size",
            (row["product_id"],),
        ).fetchall()
    return ProductInfoResult(
        found=True, product_id=row["product_id"], name=row["name"], garment_type=row["garment_type"],
        description=row["description"], colors=row["colors"], price=row["price"],
        sizes=[SizeStock(size=item["size"], quantity=item["quantity"], available=item["quantity"] > 0) for item in inventory],
    )


def get_product_price(query: str) -> StockResult:
    """Return the exact database price for a matching product."""
    with _connection() as connection:
        row = _find_product(connection, query)
    if row is None:
        return StockResult(found=False, message="No matching product was found.")
    return StockResult(found=True, product_id=row["product_id"], name=row["name"], price=row["price"], message="Price retrieved from the catalogue.")


def get_product_stock(query: str) -> StockResult:
    """Return the total quantity across all listed sizes for a product."""
    with _connection() as connection:
        row = _find_product(connection, query)
        if row is None:
            return StockResult(found=False, message="No matching product was found.")
        total = connection.execute(
            "SELECT COALESCE(SUM(quantity), 0) AS quantity FROM inventory WHERE product_id = ?",
            (row["product_id"],),
        ).fetchone()["quantity"]
    return StockResult(found=True, product_id=row["product_id"], name=row["name"], quantity=total, available=total > 0, message="Total stock across all listed sizes.")


def get_size_stock(query: str, size: str) -> StockResult:
    """Return exact stock for a product size, distinguishing missing sizes from zero stock."""
    with _connection() as connection:
        row = _find_product(connection, query)
        if row is None:
            return StockResult(found=False, size=size, message="No matching product was found.")
        inventory = connection.execute(
            """SELECT size, quantity FROM inventory
               WHERE product_id = ? AND lower(size) = lower(?)""",
            (row["product_id"], size.strip()),
        ).fetchone()
    if inventory is None:
        return StockResult(found=True, product_id=row["product_id"], name=row["name"], size=size.strip(), size_listed=False, available=False, message="That size is not listed for this product.")
    return StockResult(found=True, product_id=row["product_id"], name=row["name"], size=inventory["size"], size_listed=True, quantity=inventory["quantity"], available=inventory["quantity"] > 0, message="Size is out of stock." if inventory["quantity"] == 0 else "Size is in stock.")


def recommend_products(product_type: Optional[str] = None, min_price: Optional[float] = None, max_price: Optional[float] = None, size: Optional[str] = None, limit: int = 6) -> RecommendationResult:
    """Recommend real, currently available catalogue products using one fresh parameterized query."""
    limit = max(1, min(limit, 12))
    conditions = ["c.price >= COALESCE(?, c.price)", "c.price <= COALESCE(?, c.price)"]
    parameters: List[object] = [min_price, max_price]
    if product_type and product_type.strip():
        term = product_type.strip().lower()
        conditions.append("(lower(c.name) LIKE ? OR lower(c.garment_type) LIKE ? OR lower(c.search_tags) LIKE ?)")
        pattern = "%" + term + "%"
        parameters.extend([pattern, pattern, pattern])
    if size and size.strip():
        conditions.append("EXISTS (SELECT 1 FROM inventory si WHERE si.product_id = c.product_id AND lower(si.size) = lower(?) AND si.quantity > 0)")
        parameters.append(size.strip())
    else:
        conditions.append("EXISTS (SELECT 1 FROM inventory si WHERE si.product_id = c.product_id AND si.quantity > 0)")
    parameters.append(limit)
    with _connection() as connection:
        rows = connection.execute(
            """SELECT c.product_id, c.name, c.price, c.description, c.image_file_path,
                      COALESCE((SELECT SUM(si.quantity) FROM inventory si
                                WHERE si.product_id = c.product_id
                                  AND (? IS NULL OR lower(si.size) = lower(?))), 0) AS available_quantity
               FROM catalogue c
               WHERE """ + " AND ".join(conditions) + " ORDER BY c.price ASC, c.name LIMIT ?",
            [size, size] + parameters,
        ).fetchall()
    products = [RecommendationCard(product_id=row["product_id"], name=row["name"], price=row["price"], description=row["description"], image_url="/images/" + row["image_file_path"].lstrip("/"), available_quantity=row["available_quantity"]) for row in rows]
    criteria = ", ".join(value for value in [product_type, "min ${:.2f}".format(min_price) if min_price is not None else None, "max ${:.2f}".format(max_price) if max_price is not None else None, "size " + size if size else None] if value) or "available products"
    return RecommendationResult(criteria=criteria, count=len(products), products=products, message="Recommendations found." if products else "No matching in-stock products were found.")


def registered_tools() -> List[object]:
    """Return the database tools registered with the PydanticAI agent."""
    return [audit_tool(tool) for tool in [list_products, search_products, lookup_product, get_product_price, get_product_stock, get_size_stock, recommend_products]]
