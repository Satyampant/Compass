/** Small display helpers. Dates show in the Mac's time zone, which is Asia/Kolkata. */

export const dur = (m: number) => (m >= 60 ? (m % 60 ? `${Math.floor(m / 60)}h ${m % 60}m` : `${m / 60}h`) : `${m}m`)

export function ageDays(iso: string): number {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
}

export function savedAgo(iso: string): string {
  const d = ageDays(iso)
  return d <= 0 ? 'saved today' : `saved ${d}d ago`
}

export function slotLabel(iso: string): string {
  const at = new Date(iso)
  const today = new Date()
  const time = at.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  if (at.toDateString() === today.toDateString()) return `Today ${time}`
  return `${at.toLocaleDateString('en-GB', { weekday: 'short' })} ${time}`
}

export const SOURCE_NAMES: Record<string, string> = {
  video: 'Video', podcast: 'Podcast', repo: 'Repo', paper: 'Paper', thread: 'Thread', article: 'Article', note: 'Note',
}

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

/** A local date from a YYYY-MM-DD string, at noon so no time zone moves it. */
export const day = (iso: string) => new Date(`${iso}T12:00:00`)
export const isoDay = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
export const monthName = (iso: string) => MONTHS[day(iso).getMonth()]

/** Day number within a period and its length, both counted inclusively. */
export function periodDay(start: string, end: string, today: string): [number, number] {
  const span = (a: string, b: string) => Math.round((day(b).getTime() - day(a).getTime()) / 86_400_000) + 1
  return [span(start, today), span(start, end)]
}

/** The quarter containing a date: label, first and last month names, first and last dates. */
export function quarterSpan(iso: string) {
  const d = day(iso)
  const q = Math.floor(d.getMonth() / 3)
  const start = new Date(d.getFullYear(), q * 3, 1)
  const end = new Date(d.getFullYear(), q * 3 + 3, 0)
  return { label: `Q${q + 1} ${d.getFullYear()}`, from: MONTHS[q * 3], to: MONTHS[q * 3 + 2], start: isoDay(start), end: isoDay(end) }
}
