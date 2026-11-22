import type { CaptureKind } from '../components/QuickCapture'

/** Today. Filled in by T0.16. */
export function TodayPage({ onCapture }: { onCapture: (k: CaptureKind) => void }) {
  return (
    <div className="pagehead">
      <h1>Today</h1>
      <button className="link" onClick={() => onCapture('task')}>Add task</button>
    </div>
  )
}
