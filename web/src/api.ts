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
  direction: { aligned_min: number; planned_min: number; alignment: number | null; blocks_kept: number; blocks_total: number; planning_streak: number }
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
  draft: boolean
  done: boolean
  progress: number
  pace: number | null
  pace_status: 'on_track' | 'at_risk' | 'behind' | null
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
  on?: string
  parent_id?: number | null
  due_date?: string | null
  short?: string | null
  color?: number | null
  key_results?: { title: string; target: number; current?: number; unit?: string }[]
}

export const goalsApi = {
  list: (horizon: Horizon, on?: string) => call<Goal[]>('GET', `/v1/goals?horizon=${horizon}${on ? `&on=${on}` : ''}`),
  prompts: () => call<{ horizon: Horizon; starts: string; label: string }[]>('GET', '/v1/planning/prompts'),
  create: (goal: GoalIn) => call<Goal>('POST', '/v1/goals', goal),
  edit: (id: number, patch: Partial<{ title: string; due_date: string | null; done: boolean; short: string; color: number; parent_id: number }>) =>
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

export interface Placement {
  task_id: number
  start: string
  end: string
}

export const dayApi = {
  shutdown: (day: string, learned_line: string) => call<{ closed_at: string }>('POST', `/v1/days/${day}/shutdown`, { learned_line }),
  draft: (day: string) => call<{ date: string; open: Task[]; planned: Task[]; blocks: Block[] }>('GET', `/v1/days/${day}/plan`),
  plan: (day: string, decisions: Decision[], top: number[], blocks?: Placement[]) =>
    call<{ date: string; top: Task[] }>('POST', `/v1/days/${day}/plan`, { decisions, top, blocks }),
  propose: (day: string, task_ids: number[]) => call<Placement[]>('POST', `/v1/days/${day}/propose`, { task_ids }),
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

export interface CalendarStatus {
  connected: boolean
  error: string | null
  at: string | null
}

export const calendarApi = {
  status: () => call<CalendarStatus>('GET', '/v1/calendar'),
  resync: () => call<CalendarStatus>('POST', '/v1/calendar/resync'),
}

export interface HoursRow {
  tag: Tag | null
  planned_min: number
  done_min: number
}

export interface ReviewNumbers {
  top_done: number
  top_planned: number
  aligned_min: number
  planned_min: number
  blocks_kept: number
  blocks_total: number
  captured: number
  closed: number
  hours_by_goal: HoursRow[]
}

export interface Review {
  week_start: string
  week_end: string
  week_number: number
  prepared_at: string | null
  closed_at: string | null
  numbers: ReviewNumbers
  answers: Partial<Record<'moved' | 'off_course' | 'still_matter' | 'next_top', string>>
  expired: Item[]
  oldest: Item[]
  drafts: Goal[]
}

export const reviewApi = {
  current: () => call<Review>('GET', '/v1/reviews/current'),
  get: (week: string) => call<Review>('GET', `/v1/reviews/${week}`),
  answers: (week: string, answers: Review['answers']) => call<Review>('PUT', `/v1/reviews/${week}/answers`, { answers }),
  close: (week: string) => call<Review>('POST', `/v1/reviews/${week}/close`),
}

export interface HistoryData {
  days: { date: string; planned: boolean; closed: boolean }[]
  weeks: { week_start: string; added: number; closed: number }[]
}

export const historyApi = {
  get: () => call<HistoryData>('GET', '/v1/reviews/history'),
}
