import type { EventWithCoords } from '@/features/events/types/index.ts'

export interface GetEventsParams {
  hours?: number
}

export async function getEvents({ hours = 24 }: GetEventsParams = {}): Promise<EventWithCoords[]> {
  const url = new URL('/events', window.location.origin)
  if (hours !== undefined) {
    url.searchParams.set('hours', String(hours))
  }

  const res = await fetch(url.toString())
  if (!res.ok) {
    throw new Error(`Failed to fetch events: ${res.status} ${res.statusText}`)
  }
  return res.json()
}
