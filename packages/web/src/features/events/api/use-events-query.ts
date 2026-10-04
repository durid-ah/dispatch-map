import { useQuery } from '@tanstack/react-query'
import { getEvents, type GetEventsParams } from '@/features/events/api/get-events.ts'
import { eventKeys } from '@/features/events/api/query-keys.ts'

export function useEventsQuery(params: GetEventsParams = {}) {
  return useQuery({
    queryKey: eventKeys.list(params),
    queryFn: () => getEvents(params),
    refetchInterval: 1000 * 30, // Background polling refresh every 30s
  })
}
