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
