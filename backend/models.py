"""Pydantic request and response models for the Campus Customs chat API."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ProductCard(BaseModel):
    product_id: str
    name: str
    price: float
    image_url: Optional[str] = None


class ProductSummary(BaseModel):
    product_id: str
    name: str
    garment_type: str
    price: float


class SizeStock(BaseModel):
    size: str
    quantity: int
    available: bool


class ProductListResult(BaseModel):
    count: int
    products: List[ProductSummary]


class ProductInfoResult(BaseModel):
    found: bool
    message: Optional[str] = None
    product_id: Optional[str] = None
    name: Optional[str] = None
    garment_type: Optional[str] = None
    description: Optional[str] = None
    colors: Optional[str] = None
    price: Optional[float] = None
    sizes: List[SizeStock] = Field(default_factory=list)


class ProductSearchCard(BaseModel):
    product_id: str
    name: str
    price: float
    description: str
    image_url: str


class ProductSearchResult(BaseModel):
    query: str
    count: int
    products: List[ProductSearchCard] = Field(default_factory=list)
    message: str


class RecommendationCard(ProductSearchCard):
    available_quantity: int


class RecommendationResult(BaseModel):
    criteria: str
    count: int
    products: List[RecommendationCard] = Field(default_factory=list)
    message: str


class StockResult(BaseModel):
    found: bool
    message: Optional[str] = None
    product_id: Optional[str] = None
    name: Optional[str] = None
    price: Optional[float] = None
    size: Optional[str] = None
    size_listed: Optional[bool] = None
    quantity: Optional[int] = None
    available: Optional[bool] = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    page_context: Optional["PageContextRequest"] = None


class PageContextRequest(BaseModel):
    product_id: str = Field(min_length=1, max_length=200)


class CustomerContext(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str


class ConversationMessage(BaseModel):
    role: str
    content: str
    created_at: Optional[str] = None
    products: List[ProductSearchCard] = Field(default_factory=list)


class ChatHistoryResponse(BaseModel):
    messages: List[ConversationMessage] = Field(default_factory=list)


class VerifiedPageContext(BaseModel):
    product_id: str
    name: str
    description: str
    price: float
    colors: str
    sizes: List[SizeStock] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    products: List[ProductSearchCard] = Field(default_factory=list)
