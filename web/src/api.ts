/** Thin client for the local Compass API. */

export type ItemState = 'inbox' | 'booked' | 'learning' | 'learned' | 'let_go' | 'expired'
export type Action = 'book' | 'start' | 'finish' | 'unbook' | 'let_go'

export interface Item {
  id: number
  title: string
  url: string | null
  source_type: string
  estimate_min: number
  state: ItemState
  captured_at: string
  booked_for: string | null
  started_at: string | null
  closed_at: string | null
  note: string | null
  version: number
  actions: Action[]
}

export interface Task {
  id: number
  title: string
  estimate_min: number
  planned_date: string
  done_at: string | null
  version: number
}

export interface Today {
  date: string
  tasks: Task[]
  revisit: Item[]
  inbox_count: number
  has_items: boolean
  next_slot: string
}

export interface CaptureResult {
  capture_id: number
  outcome: 'item' | 'duplicate' | 'pending' | 'task' | 'note'
  item_id: number | null
  title: string | null
  first_saved_at: string | null
}

async function call<T>(method: string, path: string, body?: unknown, headers: Record<string, string> = {}): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json', ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `Request failed (${res.status})`)
  return data as T
}

export const api = {
  today: () => call<Today>('GET', '/v1/today'),
  items: () => call<Item[]>('GET', '/v1/learning-items?state=inbox,booked,learning,learned'),
  capture: (text: string, kind?: string) =>
    call<CaptureResult>('POST', '/v1/captures', { text, kind }, { 'Idempotency-Key': crypto.randomUUID() }),
  transition: (id: number, action: Action, extra: { booked_for?: string; note?: string } = {}) =>
    call<Item>('POST', `/v1/learning-items/${id}/transitions`, { action, ...extra }),
  addTask: (title: string, estimate_min: number) => call<Task>('POST', '/v1/tasks', { title, estimate_min }),
  editTask: (id: number, patch: Partial<{ title: string; estimate_min: number; done: boolean; planned_date: string }>) =>
    call<Task>('PATCH', `/v1/tasks/${id}`, patch),
}
