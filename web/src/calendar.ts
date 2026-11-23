/** Calendar actions shared by the banner and the time blocks card. */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { calendarApi } from './api'
import { useToast } from './components/Toast'

/** Rebuild calendar data from scratch. */
export function useResync() {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: calendarApi.resync,
    onSuccess: (s) => toast(s.connected ? 'Calendar resynced' : 'Google Calendar is still not answering'),
    onError: (err) => toast(err.message),
    onSettled: () => qc.invalidateQueries(),
  })
}
