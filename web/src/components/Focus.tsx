import { useEffect, useRef } from 'react'
import type { Task, TraceStep } from '../api'
import { Icon } from '../icons'
import { dur } from '../format'

const LABEL: Record<TraceStep['horizon'], string> = {
  year: 'Year',
  quarter: 'Quarter',
  month: 'Month',
  week: 'Week',
}

/** The chain from a task up to its year theme. Each step links to its horizon page. */
export function Trace({ steps }: { steps: TraceStep[] }) {
  if (!steps.length) return <p className="support untied">Untied: this task serves no goal yet.</p>
  return (
    <div className="trace">
      {steps.map((s, i) => (
        <span key={s.id} style={{ display: 'contents' }}>
          {i > 0 && <Icon name="right" />}
          <a href={`#${s.horizon}`}>
            <b>{LABEL[s.horizon]}</b>
            {s.title}
          </a>
        </span>
      ))}
    </div>
  )
}

function drawHills(cv: HTMLCanvasElement) {
  const w = cv.clientWidth
  const h = cv.clientHeight
  const r = Math.min(devicePixelRatio || 1, 2)
  if (!w || !h) return
  cv.width = w * r
  cv.height = h * r
  const x = cv.getContext('2d')!
  const css = getComputedStyle(document.documentElement)
  const col = (n: string) => css.getPropertyValue(n).trim()
  x.scale(r, r)
  x.fillStyle = col('--rust')
  x.globalAlpha = 0.85
  x.beginPath()
  x.arc(w * 0.72, h * 0.3, Math.min(w, h) * 0.085, 0, 7)
  x.fill()
  for (const [base, a, f, ph] of [
    [0.5, 0.16, 0.022, 1.3],
    [0.62, 0.28, 0.017, 4.1],
    [0.74, 0.44, 0.013, 2.2],
    [0.87, 0.62, 0.01, 5.6],
  ]) {
    x.globalAlpha = a
    x.fillStyle = col('--accent')
    x.beginPath()
    x.moveTo(0, h)
    for (let i = 0; i <= w; i += 3) {
      const fade = Math.min(1, i / (w * 0.45))
      x.lineTo(i, h - h * (1 - base) * fade * (1 + 0.32 * Math.sin(i * f + ph) + 0.16 * Math.sin(i * f * 2.7 + ph * 2) + 0.07 * Math.sin(i * f * 6.1 + ph)))
    }
    x.lineTo(w, h)
    x.closePath()
    x.fill()
  }
}

function Hills() {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const draw = () => ref.current && drawHills(ref.current)
    draw()
    const dark = matchMedia('(prefers-color-scheme: dark)')
    window.addEventListener('resize', draw)
    dark.addEventListener('change', draw)
    return () => {
      window.removeEventListener('resize', draw)
      dark.removeEventListener('change', draw)
    }
  }, [])
  return <canvas ref={ref} aria-hidden="true" />
}

/** The daily focus: the first of the top three not yet done, with where it leads. */
export function FocusCard({ focus, hasTop, onOpen }: { focus: { task: Task; trace: TraceStep[] } | null; hasTop: boolean; onOpen: (id: number) => void }) {
  return (
    <section className="focus">
      <Hills />
      <div className="focuscopy">
        <div className="kicker">
          <Icon name="compass" />
          Daily focus
        </div>
        {focus ? (
          <>
            <h2>{focus.task.title}</h2>
            <p>{dur(focus.task.estimate_min)}</p>
            <Trace steps={focus.trace} />
            <button className="btn outline" onClick={() => onOpen(focus.task.id)}>
              Open focus task <Icon name="arrow" />
            </button>
          </>
        ) : hasTop ? (
          <>
            <h2>Top three done</h2>
            <p>Close the day with the evening shutdown.</p>
          </>
        ) : (
          <>
            <h2>Choose today’s top three</h2>
            <p>Mark up to three tasks as top priorities. The first one not done becomes your focus.</p>
          </>
        )}
      </div>
    </section>
  )
}
