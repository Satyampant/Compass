import { useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { settingsApi, type Settings } from '../api'
import { Icon } from '../icons'
import { useToast } from '../components/Toast'

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
type NumberKey = { [K in keyof Settings]: Settings[K] extends number ? K : never }[keyof Settings]
type TimeKey = 'morning_run_time' | 'shutdown_nudge_time' | 'review_time'

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="setting">
      <span>
        {label}
        {hint && <small className="muted">{hint}</small>}
      </span>
      {children}
    </label>
  )
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="card">
      <div className="cardhead">
        <h2>{title}</h2>
      </div>
      <div className="section">{children}</div>
    </section>
  )
}

function Form({ initial }: { initial: Settings }) {
  const [s, setS] = useState(initial)
  const [days, setDays] = useState(initial.resurface_days.join(', '))
  const qc = useQueryClient()
  const toast = useToast()
  const save = useMutation({
    mutationFn: () => {
      const changes = { ...s, resurface_days: days.split(/[,\s]+/).filter(Boolean).map(Number) }
      const changed = Object.fromEntries(Object.entries(changes).filter(([k, v]) => JSON.stringify(v) !== JSON.stringify(initial[k as keyof Settings])))
      return settingsApi.put(changed)
    },
    onSuccess: () => {
      qc.invalidateQueries()
      toast('Settings saved')
    },
    onError: (err) => toast(err.message),
  })
  const num = (key: NumberKey, min = 0, max = 999) => (
    <input type="number" aria-label={key} min={min} max={max} value={s[key]} onChange={(e) => setS({ ...s, [key]: Number(e.target.value) })} />
  )
  const at = (key: TimeKey) => <input type="time" aria-label={key} value={s[key]} onChange={(e) => setS({ ...s, [key]: e.target.value })} />
  const setSlot = (i: number, patch: Partial<Settings['learning_slots'][number]>) => setS({ ...s, learning_slots: s.learning_slots.map((x, j) => (j === i ? { ...x, ...patch } : x)) })

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        save.mutate()
      }}
    >
      <div className="cols even">
        <div className="stack">
          <Group title="Learning queue">
            <Field label="Resurface on days" hint="after capture">
              <input type="text" aria-label="resurface_days" value={days} onChange={(e) => setDays(e.target.value)} />
            </Field>
            <Field label="Last ask on day">{num('last_ask_day', 1, 365)}</Field>
            <Field label="Archive after the last ask" hint="days">{num('last_ask_grace_days', 0, 30)}</Field>
            <Field label="Items on the revisit list" hint="a day">{num('revisit_per_day', 1, 20)}</Field>
            <Field label="Default estimate" hint="minutes">{num('default_estimate_min', 1, 600)}</Field>
            <Field label="Items in Learning at once">{num('max_in_learning', 1, 10)}</Field>
          </Group>
          <Group title="Learning slots">
            {s.learning_slots.map((slot, i) => (
              <div className="slotrow" key={i}>
                <select aria-label={`Slot ${i + 1} day`} value={slot.weekday} onChange={(e) => setSlot(i, { weekday: Number(e.target.value) })}>
                  {WEEKDAYS.map((d, n) => (
                    <option key={d} value={n}>
                      {d}
                    </option>
                  ))}
                </select>
                <input type="time" aria-label={`Slot ${i + 1} time`} value={slot.time} onChange={(e) => setSlot(i, { time: e.target.value })} />
                <button type="button" className="link" disabled={s.learning_slots.length === 1} onClick={() => setS({ ...s, learning_slots: s.learning_slots.filter((_, j) => j !== i) })}>
                  Remove
                </button>
              </div>
            ))}
            <button type="button" className="link" onClick={() => setS({ ...s, learning_slots: [...s.learning_slots, { weekday: 0, time: '16:00' }] })}>
              <Icon name="plus" />
              Add a slot
            </button>
            <Field label="Block length" hint="minutes">{num('learning_block_min', 15, 240)}</Field>
          </Group>
        </div>
        <div className="stack">
          <Group title="Days and weeks">
            <Field label="Day starts">
              <input type="time" aria-label="day start" value={s.day_window[0]} onChange={(e) => setS({ ...s, day_window: [e.target.value, s.day_window[1]] })} />
            </Field>
            <Field label="Day ends">
              <input type="time" aria-label="day end" value={s.day_window[1]} onChange={(e) => setS({ ...s, day_window: [s.day_window[0], e.target.value] })} />
            </Field>
            <Field label="Top priorities a day">{num('top_priorities', 1, 10)}</Field>
            <Field label="Weekday capacity" hint="hours">{num('capacity_weekday_hours', 0, 24)}</Field>
            <Field label="Weekend capacity" hint="hours">{num('capacity_weekend_hours', 0, 24)}</Field>
            <Field label="Week capacity" hint="hours">{num('capacity_week_hours', 0, 168)}</Field>
          </Group>
          <Group title="Nudges and runs">
            <Field label="Morning run">{at('morning_run_time')}</Field>
            <Field label="Shutdown nudge">{at('shutdown_nudge_time')}</Field>
            <Field label="Weekly review ready" hint="on Sunday">{at('review_time')}</Field>
            <Field label="Block reminder" hint="minutes before">{num('block_reminder_min', 0, 120)}</Field>
            <Field label="Nudges a day">{num('nudges_per_day', 0, 20)}</Field>
          </Group>
          <Group title="Goals and system">
            <Field label="On track within" hint="points of pace">{num('pace_on_track_points', 0, 100)}</Field>
            <Field label="At risk within" hint="points of pace">{num('pace_at_risk_points', 0, 100)}</Field>
            <Field label="Time zone">
              <input type="text" aria-label="timezone" value={s.timezone} onChange={(e) => setS({ ...s, timezone: e.target.value })} />
            </Field>
            <Field label="Backup folder" hint="empty means data/backups">
              <input type="text" aria-label="backup_dir" value={s.backup_dir ?? ''} onChange={(e) => setS({ ...s, backup_dir: e.target.value || null })} />
            </Field>
          </Group>
        </div>
      </div>
      <div className="actions">
        <button className="btn primary" disabled={save.isPending}>
          Save settings
        </button>
      </div>
    </form>
  )
}

/** The rules from PRD section 08. Changing slot times regenerates the coming slots. */
export function SettingsPage() {
  const { data } = useQuery({ queryKey: ['settings'], queryFn: settingsApi.get })
  return (
    <>
      <div className="pagehead">
        <div>
          <div className="over kicker" style={{ color: 'var(--rust)' }}>
            <Icon name="compass" />
            The rules Compass works by
          </div>
          <h1>Settings</h1>
        </div>
      </div>
      {data && <Form key={JSON.stringify(data)} initial={data} />}
    </>
  )
}
