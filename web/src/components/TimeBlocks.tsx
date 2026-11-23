import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { blocksApi, type Block, type Today } from '../api'
import { useToast } from './Toast'
import { useResync } from '../calendar'
import { Dot } from './goals'

const hm = (iso: string) => new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })

/** The current minute, updated every thirty seconds so the highlight moves on its own. */
function useNow(): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 30_000)
    return () => window.clearInterval(id)
  }, [])
  return now
}

function chip(block: Block, now: boolean) {
  if (now) return <span className="chip good">Now</span>
  if (block.kind === 'learning') return <span className="chip">{block.item_id ? 'From queue' : 'Open slot'}</span>
  if (block.status === 'missed') return <span className="chip warn">Missed</span>
  return <span />
}

type Row = { at: number; mark?: string; block?: Block }

/** The day from 08:00 to 20:00: meetings and blocks together, the current one highlighted. */
export function TimeBlocks({ data }: { data: Today }) {
  const now = useNow()
  const resync = useResync()
  const qc = useQueryClient()
  const toast = useToast()
  const swap = useMutation({
    mutationFn: blocksApi.swap,
    onSuccess: (b) => toast(b.item_id ? `Swapped in: ${b.title.replace(/^Learning: /, '')}` : 'Nothing else fits this slot'),
    onError: (err) => toast(err.message),
    onSettled: () => qc.invalidateQueries(),
  })
  const rows: Row[] = [
    ...data.blocks.map((b) => ({ at: new Date(b.start).getTime(), block: b })),
    ...data.marks.map((m) => ({ at: new Date(m.at).getTime(), mark: `${hm(m.at)} · ${m.label}` })),
  ].sort((a, b) => a.at - b.at)
  const minutes = data.blocks.filter((b) => b.source === 'compass').reduce((s, b) => s + (new Date(b.end).getTime() - new Date(b.start).getTime()) / 60_000, 0)

  return (
    <section className="card">
      <div className="cardhead">
        <h2>Time blocks</h2>
        <span className="cardtools">
          <span className="chip">{Math.round((minutes / 60) * 10) / 10}h blocked</span>
          <button className="link" disabled={resync.isPending} onClick={() => resync.mutate()} title="Rebuild calendar data from scratch">
            Resync
          </button>
        </span>
      </div>
      <div className="section" data-testid="blocks">
        {rows.map((r) => {
          if (r.mark)
            return (
              <div className="mark" key={`m${r.at}`}>
                {r.mark}
              </div>
            )
          const b = r.block!
          const current = new Date(b.start).getTime() <= now && now < new Date(b.end).getTime()
          return (
            <div className={`slot ${current ? 'now' : ''} ${b.source === 'calendar' ? 'meeting' : ''}`} key={b.id}>
              <span className="t">
                {hm(b.start)} – {hm(b.end)}
              </span>
              <span className="name">
                <Dot color={b.tag?.color} />
                <span>{b.title}</span>
              </span>
              {b.protected && b.item_id && b.status === 'planned' && new Date(b.start).getTime() > now ? (
                <button className="link" onClick={() => swap.mutate(b.id)} aria-label={`Swap ${b.title}`}>
                  Swap
                </button>
              ) : (
                chip(b, current)
              )}
            </div>
          )
        })}
        {data.blocks.length === 0 && <p className="empty">No meetings or blocks today.</p>}
      </div>
    </section>
  )
}
