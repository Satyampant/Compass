import { useQuery } from '@tanstack/react-query'
import { calendarApi } from '../api'
import { useResync } from '../calendar'

/** Shown on every screen while Google Calendar is not connected. Everything else keeps working. */
export function CalendarBanner() {
  const { data } = useQuery({ queryKey: ['calendar'], queryFn: calendarApi.status, refetchInterval: 60_000 })
  const resync = useResync()
  if (!data || data.connected) return null
  const signedOut = /not signed in|not set|turned off|not checked/.test(data.error ?? '')
  return (
    <section className="card banner calendar-banner" role="status">
      <div>
        <p className="kicker">Calendar not connected</p>
        <p className="support">
          {signedOut
            ? 'Meetings and learning blocks appear once Compass is signed in to Google (make google-signin). Everything else works as usual.'
            : `Google Calendar stopped answering: ${data.error}. Everything else works as usual.`}
        </p>
      </div>
      <button className="btn outline" disabled={resync.isPending} onClick={() => resync.mutate()}>
        Try again
      </button>
    </section>
  )
}
