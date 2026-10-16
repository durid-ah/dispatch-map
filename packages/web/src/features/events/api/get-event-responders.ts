import type { EventRespondersEnvelope } from '@/features/events/types/index.ts'

export async function getEventResponders(externalId: string): Promise<EventRespondersEnvelope> {
  const url = new URL(`/events/${encodeURIComponent(externalId)}/responders`, window.location.origin)

  const res = await fetch(url.toString())
  if (!res.ok) {
    if (res.status === 404) {
      throw new Error(`Event not found: ${externalId}`)
    }
    throw new Error(`Failed to fetch responders: ${res.status} ${res.statusText}`)
  }
  return res.json()
}
