export type Product = {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string
  search_tags: string
  image_url: string
  price: number
}

export type Inventory = { size: string; quantity: number }
export type ProductDetail = Product & { inventory: Inventory[] }
export type User = { id: number; first_name: string; last_name: string; email: string }
export type ChatSearchProduct = { product_id: string; name: string; price: number; description: string; image_url: string }
export type ChatHistoryMessage = { role: 'user' | 'assistant'; content: string; created_at?: string; products?: ChatSearchProduct[] }
