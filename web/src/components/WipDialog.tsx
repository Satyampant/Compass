import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Item } from '../api'
import { Dialog } from './Dialog'
import { useToast } from './Toast'

/** Starting a third item: finish or return one of the two in Learning first. */
export function WipDialog({ starting, learning, onFinish, onClose }: { starting: Item; learning: Item[]; onFinish: (item: Item) => void; onClose: () => void }) {
  const qc = useQueryClient()
  const toast = useToast()
  const swap = useMutation({
    mutationFn: async (back: Item) => {
      await api.transition(back.id, 'return')
      return api.transition(starting.id, 'start')
    },
    onSuccess: () => {
      toast('Returned one to booked and started the new one')
      onClose()
    },
    onError: (err) => toast(err.message),
    onSettled: () => qc.invalidateQueries(),
  })
  return (
    <Dialog title="Two items are in Learning" onClose={onClose}>
      <p className="support">To start “{starting.title}”, finish one of these or return it to booked. Returning keeps your progress and takes the next free learning block.</p>
      {learning.map((i) => (
        <div className="decide" key={i.id}>
          <span className="title">{i.title}</span>
          <div className="strip">
            <button className="soft" onClick={() => onFinish(i)}>
              Mark learned
            </button>
            <button className="soft" disabled={swap.isPending} onClick={() => swap.mutate(i)}>
              Return to booked
            </button>
          </div>
        </div>
      ))}
    </Dialog>
  )
}
