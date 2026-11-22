/** Line icons from the mockup. */

const PATHS = {
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2"/>',
  queue: '<path d="M4 5h16M4 12h16M4 19h10"/>',
  week: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18"/>',
  month: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18m-13 4h1m4 0h1m4 0h1m-11 3h1m4 0h1"/>',
  quarter: '<circle cx="12" cy="12" r="9"/><path d="M12 3v9h9"/>',
  year: '<path d="M5 21V4c6-5 8 5 15 0v10c-6 4-10-5-15 0"/>',
  review: '<path d="M4 20h16M7 16v-5m5 5V5m5 11v-8"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="m15.9 8.1-2.4 5.4-5.4 2.4 2.4-5.4z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  arrow: '<path d="M4 12h15m-5-5 5 5-5 5"/>',
  right: '<path d="m9 5 7 7-7 7"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
  check: '<path d="m4 12 5 5L20 6"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  close: '<path d="m5 5 14 14M19 5 5 19"/>',
  play: '<path d="M7 4v16l13-8z"/>',
  doc: '<path d="M6 3h8l4 4v14H6zM14 3v4h4M9 12h6M9 16h6"/>',
  book: '<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3zM5 17a3 3 0 0 1 3-3h11"/>',
  mark: '<path d="M6 3h12v18l-6-4.5L6 21z"/>',
} as const

export type IconName = keyof typeof PATHS

export function Icon({ name }: { name: IconName }) {
  return <svg className="ic" aria-hidden="true" viewBox="0 0 24 24" dangerouslySetInnerHTML={{ __html: PATHS[name] }} />
}

export function sourceIcon(source: string): IconName {
  return source === 'video' || source === 'podcast' ? 'play' : source === 'note' ? 'mark' : source === 'book' ? 'book' : 'doc'
}
