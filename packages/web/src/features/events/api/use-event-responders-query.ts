import { useQuery } from '@tanstack/react-query'
import { getEventResponders } from '@/features/events/api/get-event-responders.ts'
import { eventKeys } from '@/features/events/api/query-keys.ts'

export function useEventRespondersQuery(externalId?: string | null) {
  return useQuery({
    queryKey: externalId ? eventKeys.responders(externalId) : ['events', 'responders', null],
    queryFn: () => {
      if (!externalId) {
        throw new Error('externalId is required to fetch responders')
      }
      return getEventResponders(externalId)
    },
    enabled: Boolean(externalId),
    staleTime: 1000 * 15,
    refetchInterval: 1000 * 30,
  })
}
