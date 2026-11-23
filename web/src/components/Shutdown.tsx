import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { dayApi, type Today } from '../api'
import { useToast } from './Toast'

const STEPS = ['Mark what got done, move what didn’t', 'Decide on today’s captures', 'Pick tomorrow’s top three']

/** The evening shutdown: four steps. Ticking the fourth closes the day with one learned line. */
export function Shutdown({ data, onPlan }: { data: Today; onPlan: () => void }) {
  const [ticked, setTicked] = useState([false, false, false])
  const [line, setLine] = useState('')
  const [closing, setClosing] = useState(false)
  const qc = useQueryClient()
  const toast = useToast()
  const close = useMutation({
    mutationFn: () => dayApi.shutdown(data.date, line.trim()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['today'] })
      toast('Day closed. See you tomorrow.')
    },
    onError: (err) => {
      setClosing(false)
      toast(err.message)
    },
  })
  const done = (i: number) => ticked[i] || (i === 2 && data.tomorrow_planned)
  const ready = STEPS.every((_, i) => done(i)) && !!line.trim()

  if (data.closed_at) {
    const at = new Date(data.closed_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
    return (
      <section className="card ritual">
        <div className="cardhead">
          <h2>Evening shutdown</h2>
          <span className="chip good">Closed {at}</span>
        </div>
        <p className="support">What I learned today</p>
        <p className="learned">{data.learned_line}</p>
      </section>
    )
  }

  return (
    <section className="card ritual">
      <div className="cardhead">
        <h2>Evening shutdown</h2>
        <span className="chip">10 minutes</span>
      </div>
      <p className="support">Close today before tomorrow starts.</p>
      {STEPS.map((step, i) => (
        <label key={step} htmlFor={`r${i}`}>
          <input type="checkbox" id={`r${i}`} checked={done(i)} disabled={i === 2 && data.tomorrow_planned} onChange={(e) => setTicked(ticked.map((t, j) => (j === i ? e.target.checked : t)))} />
          {step}
          {i === 1 && (
            <a className="link" href="#learn">
              Queue
            </a>
          )}
          {i === 2 && !data.tomorrow_planned && (
            <button
              type="button"
              className="link"
              onClick={(e) => {
                e.preventDefault()
                onPlan()
              }}
            >
              Plan tomorrow
            </button>
          )}
        </label>
      ))}
      <label htmlFor="r3">
        <input
          type="checkbox"
          id="r3"
          checked={closing}
          disabled={!ready || closing}
          onChange={() => {
            setClosing(true)
            close.mutate()
          }}
        />
        Write one line: what did I learn?
      </label>
      <input type="text" aria-label="What did I learn today" placeholder="One line" maxLength={500} value={line} onChange={(e) => setLine(e.target.value)} />
    </section>
  )
}
