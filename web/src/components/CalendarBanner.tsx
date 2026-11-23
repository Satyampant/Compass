import { useQuery } from '@tanstack/react-query'
import { calendarApi } from '../api'
import { useResync } from '../calendar'

/** Shown on every screen when a calendar that was connected stops answering. Before the first
 * sign-in there is nothing to warn about; the status page shows the calendar row. */
export function CalendarBanner() {
  const { data } = useQuery({ queryKey: ['calendar'], queryFn: calendarApi.status, refetchInterval: 60_000 })
  const resync = useResync()
  if (!data || data.connected || !data.ever_connected) return null
  return (
    <section className="card banner calendar-banner" role="status">
      <div>
        <p className="kicker">Calendar not connected</p>
        <p className="support">
          Google Calendar stopped answering: {data.error}. Everything else works as usual.
        </p>
      </div>
      <button className="btn outline" disabled={resync.isPending} onClick={() => resync.mutate()}>
        Try again
      </button>
    </section>
  )
}
