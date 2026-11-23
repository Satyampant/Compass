import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { reviewApi, type Item, type Review, type ReviewNumbers } from '../api'
import { Icon } from '../icons'
import { day } from '../format'
import { Dot } from '../components/goals'
import { useToast } from '../components/Toast'
import { useItemTransition } from '../useTransition'
import { History } from '../components/History'

const h = (min: number) => Math.round((min / 60) * 10) / 10

const PROMPTS: [keyof Review['answers'], string, string][] = [
  ['moved', 'What moved a goal forward?', ''],
  ['off_course', 'What pulled me off course?', ''],
  ['still_matter', 'Which saved items still matter?', 'The oldest items in the queue are listed below'],
  ['next_top', 'Next week’s top three', 'One per line. They become next week’s draft outcomes'],
]

function Numbers({ n }: { n: ReviewNumbers }) {
  const boxes: [string, number, string, string][] = [
    ['Top three done', n.top_done, `/ ${n.top_planned}`, n.top_planned ? `${Math.round((n.top_done / n.top_planned) * 100)}% of ranked tasks` : 'Nothing ranked'],
    ['Hours on goals', h(n.aligned_min), `/ ${h(n.planned_min)}h`, n.planned_min ? `${Math.round((n.aligned_min / n.planned_min) * 100)}% aligned` : 'Nothing planned'],
    ['Learning blocks kept', n.blocks_kept, `/ ${n.blocks_total}`, n.blocks_total ? `${n.blocks_total - n.blocks_kept} not kept` : 'No protected slots'],
    ['Queue in and out', n.captured, `→ ${n.closed}`, n.captured > n.closed ? `${n.captured - n.closed} more in than out` : n.captured < n.closed ? `${n.closed - n.captured} more out than in` : 'As much out as in'],
  ]
  return (
    <div className="hgrid">
      {boxes.map(([k, a, b, note]) => (
        <div className="hbox" key={k}>
          <p className="kicker">{k}</p>
          <p className="figure">
            {a} <small>{b}</small>
          </p>
          <p className="note">{note}</p>
        </div>
      ))}
    </div>
  )
}

function Hours({ rows }: { rows: ReviewNumbers['hours_by_goal'] }) {
  const max = Math.max(1, ...rows.map((r) => Math.max(r.planned_min, r.done_min)))
  return (
    <section className="card">
      <div className="cardhead">
        <h2>Where the hours went</h2>
        <span className="chip">tick = planned</span>
      </div>
      <div className="section">
        {rows.map((r) => (
          <div className="hbar" key={r.tag?.id ?? 'untied'}>
            <span className="gtag">
              <Dot color={r.tag?.color} />
              {r.tag ? r.tag.short || r.tag.title : 'Untied'}
            </span>
            <div className="pace">
              <i style={{ width: `${(r.done_min / max) * 100}%`, background: r.tag?.color ? `var(--g${r.tag.color})` : 'var(--rust)' }} />
              <em style={{ left: `${(r.planned_min / max) * 100}%` }} />
            </div>
            <span className="num">
              {h(r.done_min)} / {h(r.planned_min)}h
            </span>
          </div>
        ))}
        {rows.length === 0 && <p className="empty">Nothing planned this week.</p>}
      </div>
    </section>
  )
}

function ItemList({ title, items, empty }: { title: string; items: Item[]; empty: string }) {
  const move = useItemTransition()
  return (
    <>
      <p className="kicker sub-k">{title}</p>
      {items.map((i) => (
        <div className="decide" key={i.id}>
          <span className="title">{i.title}</span>
          {i.actions.length > 0 && (
            <div className="strip">
              {i.actions.includes('book') && (
                <button className="soft" onClick={() => move.mutate({ id: i.id, action: 'book' })}>
                  Book
                </button>
              )}
              {i.actions.includes('let_go') && (
                <button className="soft" onClick={() => move.mutate({ id: i.id, action: 'let_go' })}>
                  Let go
                </button>
              )}
            </div>
          )}
        </div>
      ))}
      {items.length === 0 && <p className="empty">{empty}</p>}
    </>
  )
}

function Reflect({ review }: { review: Review }) {
  const [answers, setAnswers] = useState(review.answers)
  const qc = useQueryClient()
  const toast = useToast()
  const closed = !!review.closed_at
  const save = useMutation({ mutationFn: () => reviewApi.answers(review.week_start, answers), onError: (e) => toast(e.message) })
  const close = useMutation({
    mutationFn: async () => {
      await reviewApi.answers(review.week_start, answers)
      return reviewApi.close(review.week_start)
    },
    onSuccess: (r) => {
      qc.invalidateQueries({ predicate: (q) => q.queryKey[1] !== 'current' })
      toast(`Week ${r.week_number} closed. ${r.drafts.length} outcome${r.drafts.length === 1 ? '' : 's'} drafted for next week.`)
    },
    onError: (e) => toast(e.message),
  })
  return (
    <section className="card">
      <div className="cardhead">
        <h2>Reflect</h2>
        <span className="chip">{closed ? 'Closed' : `feeds week ${review.week_number + 1}`}</span>
      </div>
      {PROMPTS.map(([key, q, placeholder]) => (
        <div key={key}>
          <label className="q" htmlFor={`q-${key}`}>
            {q}
          </label>
          <textarea id={`q-${key}`} readOnly={closed} placeholder={placeholder} value={answers[key] ?? ''} onChange={(e) => setAnswers({ ...answers, [key]: e.target.value })} onBlur={() => !closed && save.mutate()} />
        </div>
      ))}
      {!closed && (
        <div className="actions">
          <button className="btn primary" disabled={close.isPending} onClick={() => close.mutate()}>
            Close week and plan week {review.week_number + 1}
          </button>
        </div>
      )}
      {closed && (
        <p className="support" style={{ marginTop: 14 }}>
          Next week’s outcomes are drafted.{' '}
          <a className="link" href="#week">
            Choose their milestones on This week <Icon name="arrow" />
          </a>
        </p>
      )}
    </section>
  )
}

/** The weekly review: the week's numbers, four prompts, and closing the week. The page stays on
 * the week it opened with, so closing it shows the closed week rather than the next one. */
export function ReviewPage() {
  const current = useQuery({ queryKey: ['review', 'current'], queryFn: reviewApi.current, staleTime: Infinity })
  const week = current.data?.week_start
  const { data: review } = useQuery({ queryKey: ['review', week], queryFn: () => reviewApi.get(week!), enabled: !!week })
  if (!review) return null
  const range = `${day(review.week_start).getDate()} – ${day(review.week_end).toLocaleDateString('en-GB', { day: 'numeric', month: 'long' })}`
  return (
    <>
      <div className="pagehead">
        <div>
          <div className="over kicker" style={{ color: 'var(--rust)' }}>
            <Icon name="review" />
            {review.closed_at ? 'Closed · numbers frozen' : 'Sunday review · 20 minutes'}
          </div>
          <h1>Week {review.week_number} in review</h1>
        </div>
        <span>{range}</span>
      </div>
      <Numbers n={review.numbers} />
      <div className="cols even" style={{ marginTop: 20 }}>
        <div className="stack">
          <Hours rows={review.numbers.hours_by_goal} />
          <History />
          <section className="card">
            <div className="cardhead">
              <h2>Saved items</h2>
            </div>
            <ItemList title="Expired this week" items={review.expired} empty="Nothing expired this week." />
            <ItemList title="Oldest in the inbox" items={review.oldest} empty="The inbox is empty." />
          </section>
        </div>
        <Reflect key={review.week_start + (review.closed_at ?? '')} review={review} />
      </div>
    </>
  )
}
