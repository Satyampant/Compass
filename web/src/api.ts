/** Thin client for the local Compass API. */

export type ItemState = 'inbox' | 'booked' | 'learning' | 'learned' | 'let_go' | 'expired'
export type Action = 'book' | 'start' | 'finish' | 'return' | 'unbook' | 'let_go'

export interface Item {
  id: number
  title: string
  url: string | null
  source_type: string
  estimate_min: number
  progress_min: number
  state: ItemState
  captured_at: string
  booked_for: string | null
  started_at: string | null
  closed_at: string | null
  note: string | null
  goal_id: number | null
  reason: string | null
  tag: Tag | null
  version: number
  actions: Action[]
}

/** The quarter goal a task or item serves. */
export interface Tag {
  id: number
  title: string
  short: string | null
  color: number | null
}

export interface Task {
  id: number
  title: string
  estimate_min: number
  planned_date: string
  done_at: string | null
  goal_id: number | null
  tag: Tag | null
  top_rank: number | null
  version: number
}

export interface Today {
  date: string
  focus: { task: Task; trace: TraceStep[] } | null
  top_limit: number
  closed_at: string | null
  learned_line: string | null
  tomorrow_planned: boolean
  tasks: Task[]
  blocks: Block[]
  marks: { at: string; label: string }[]
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
  capture: (text: string, kind?: string, links: { goal_id?: number | null; reason?: string } = {}) =>
    call<CaptureResult>('POST', '/v1/captures', { text, kind, ...links }, { 'Idempotency-Key': crypto.randomUUID() }),
  transition: (id: number, action: Action, extra: { booked_for?: string; note?: string } = {}) =>
    call<Item>('POST', `/v1/learning-items/${id}/transitions`, { action, ...extra }),
  addTask: (title: string, estimate_min: number, goal_id: number | null = null) => call<Task>('POST', '/v1/tasks', { title, estimate_min, goal_id }),
  editTask: (id: number, patch: Partial<{ title: string; estimate_min: number; done: boolean; planned_date: string; goal_id: number | null }>) =>
    call<Task>('PATCH', `/v1/tasks/${id}`, patch),
  saveProgress: (id: number, minutes: number) => call<Item>('POST', `/v1/learning-items/${id}/progress`, { minutes }),
  setTop: (day: string, task_ids: number[]) => call<Task[]>('PUT', `/v1/days/${day}/top-three`, { task_ids }),
  editItem: (id: number, patch: Partial<{ title: string; estimate_min: number; goal_id: number | null; reason: string | null }>) =>
    call<Item>('PATCH', `/v1/learning-items/${id}`, patch),
}

export type Horizon = 'year' | 'quarter' | 'month' | 'week'

export interface KeyResult {
  id: number
  title: string
  target: number
  current: number
  unit: string
  version: number
}

export interface Goal {
  id: number
  horizon: Horizon
  title: string
  parent_id: number | null
  period_start: string
  period_end: string
  due_date: string | null
  short: string | null
  color: number | null
  done: boolean
  progress: number
  key_results: KeyResult[]
  version: number
}

export interface TraceStep {
  id: number
  horizon: Horizon
  title: string
  short: string | null
  color: number | null
}

export interface GoalIn {
  horizon: Horizon
  title: string
  parent_id?: number | null
  due_date?: string | null
  short?: string | null
  color?: number | null
  key_results?: { title: string; target: number; current?: number; unit?: string }[]
}

export const goalsApi = {
  list: (horizon: Horizon) => call<Goal[]>('GET', `/v1/goals?horizon=${horizon}`),
  create: (goal: GoalIn) => call<Goal>('POST', '/v1/goals', goal),
  edit: (id: number, patch: Partial<{ title: string; due_date: string | null; done: boolean; short: string; color: number }>) =>
    call<Goal>('PATCH', `/v1/goals/${id}`, patch),
  remove: (id: number) => fetch(`/v1/goals/${id}`, { method: 'DELETE' }),
  trace: (id: number) => call<TraceStep[]>('GET', `/v1/goals/${id}/trace`),
  editKeyResult: (id: number, patch: Partial<{ current: number; target: number; title: string }>) =>
    call<KeyResult>('PATCH', `/v1/key-results/${id}`, patch),
}

export interface DayColumn {
  date: string
  tasks: Task[]
  planned_min: number
  capacity_min: number
  over: boolean
}

export interface Week {
  start: string
  days: DayColumn[]
  planned_min: number
  capacity_min: number
  over: boolean
}

export const weekApi = {
  get: () => call<Week>('GET', '/v1/week'),
}

export type DecisionAction = 'tomorrow' | 'reschedule' | 'drop'
export interface Decision {
  task_id: number
  action: DecisionAction
  to?: string
}

export const dayApi = {
  shutdown: (day: string, learned_line: string) => call<{ closed_at: string }>('POST', `/v1/days/${day}/shutdown`, { learned_line }),
  draft: (day: string) => call<{ date: string; open: Task[]; planned: Task[] }>('GET', `/v1/days/${day}/plan`),
  plan: (day: string, decisions: Decision[], top: number[]) => call<{ date: string; top: Task[] }>('POST', `/v1/days/${day}/plan`, { decisions, top }),
}

export interface Block {
  id: number
  kind: 'meeting' | 'task' | 'learning'
  source: 'calendar' | 'compass'
  title: string
  start: string
  end: string
  task_id: number | null
  item_id: number | null
  item_url: string | null
  protected: boolean
  status: string
  tag: Tag | null
  version: number
}

export const blocksApi = {
  swap: (id: number) => call<Block>('POST', `/v1/blocks/${id}/swap`),
}
