import type { ChatHistoryMessage, ChatSearchProduct, Product, ProductDetail, User } from './types'

export async function getProducts(): Promise<Product[]> {
  const response = await fetch('/api/products')
  if (!response.ok) throw new Error('Unable to load products.')
  return response.json()
}

export async function getProduct(productId: string): Promise<ProductDetail> {
  const response = await fetch(`/api/products/${encodeURIComponent(productId)}`)
  if (!response.ok) throw new Error('Product not found.')
  return response.json()
}

async function authRequest(path: string, body?: Record<string, string>) {
  const response = await fetch(path, {
    method: body ? 'POST' : 'GET',
    credentials: 'include',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || 'Something went wrong.')
  return data
}

export async function registerAccount(values: Record<string, string>): Promise<User> {
  return (await authRequest('/api/auth/register', values)).user
}

export async function loginAccount(values: Record<string, string>): Promise<User> {
  return (await authRequest('/api/auth/login', values)).user
}

export async function getCurrentUser(): Promise<User | null> {
  return (await authRequest('/api/auth/me')).user
}

export async function logoutAccount(): Promise<void> {
  await authRequest('/api/auth/logout', {})
}

export async function sendChatMessage(message: string, productId?: string): Promise<{ reply: string; products: ChatSearchProduct[] }> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, page_context: productId ? { product_id: productId } : null }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || 'The assistant could not respond.')
  return data
}

export async function getChatHistory(): Promise<ChatHistoryMessage[]> {
  const response = await fetch('/api/chat/history', { credentials: 'include' })
  if (!response.ok) throw new Error('Chat history is available after login.')
  const data = await response.json()
  return data.messages
}
