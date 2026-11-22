import { useState } from 'react'
import type { Item } from '../api'
import { Icon } from '../icons'
import { SOURCE_NAMES, ageDays, slotLabel } from '../format'
import { useItemTransition } from '../useTransition'
import { Dialog } from './Dialog'

function where(item: Item): string {
  const d = ageDays(item.captured_at)
  switch (item.state) {
    case 'inbox':
      return d <= 0 ? 'Saved today' : `Saved ${d} day${d === 1 ? '' : 's'} ago`
    case 'booked':
      return `Booked for ${slotLabel(item.booked_for!)}`
    case 'learning':
      return 'In progress'
    default:
      return item.note || 'Learned'
  }
}

/** A learning item with only the moves that are valid for its state. */
export function ItemDialog({ item, onClose }: { item: Item; onClose: () => void }) {
  const move = useItemTransition()
  const [when, setWhen] = useState('')
  const [note, setNote] = useState('')
  const can = (a: string) => item.actions.includes(a as Item['actions'][number])
  const run = (action: Item['actions'][number], extra = {}) => {
    move.mutate({ id: item.id, action, ...extra })
    onClose()
  }
  return (
    <Dialog title="Learning item" onClose={onClose}>
      <p className="kicker">
        {SOURCE_NAMES[item.source_type] ?? item.source_type} · {item.estimate_min} min
      </p>
      <h3 style={{ marginTop: 8 }}>{item.title}</h3>
      {item.url && (
        <p className="support">
          <a className="link" href={item.url} target="_blank" rel="noreferrer">
            Open link <Icon name="arrow" />
          </a>
        </p>
      )}
      <p className="support" style={{ marginTop: 12 }}>
        {where(item)}
      </p>
      {can('book') && (
        <>
          <label className="q" htmlFor="bwhen">
            Or pick a time
          </label>
          <input id="bwhen" type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} />
        </>
      )}
      {can('finish') && (
        <>
          <label className="q" htmlFor="bnote">
            What did you take from it, or do with it?
          </label>
          <textarea id="bnote" value={note} onChange={(e) => setNote(e.target.value)} />
        </>
      )}
      <div className="actions">
        {can('book') && (
          <button className="btn primary" onClick={() => run('book', when ? { booked_for: new Date(when).toISOString() } : {})}>
            <Icon name="plus" />
            {when ? 'Book this time' : 'Book next learning block'}
          </button>
        )}
        {can('start') && (
          <button className="btn primary" onClick={() => run('start')}>
            <Icon name="play" />
            Start now
          </button>
        )}
        {can('finish') && (
          <button className="btn primary" onClick={() => run('finish', note.trim() ? { note: note.trim() } : {})}>
            <Icon name="check" />
            Mark learned
          </button>
        )}
        {can('unbook') && (
          <button className="btn outline" onClick={() => run('unbook')}>
            Back to inbox
          </button>
        )}
        {can('let_go') && (
          <button className="btn outline" onClick={() => run('let_go')}>
            Let go
          </button>
        )}
      </div>
    </Dialog>
  )
}
