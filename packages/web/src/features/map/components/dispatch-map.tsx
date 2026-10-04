import { useEffect, useMemo } from 'react'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import type { EventWithCoords } from '@/features/events/types/index.ts'
import { EventMarker } from '@/features/map/components/event-marker.tsx'

export interface DispatchMapProps {
  events?: EventWithCoords[]
  selectedEventId?: number | null
  onSelectEvent?: (event: EventWithCoords) => void
  center?: [number, number]
  zoom?: number
  className?: string
}

const DEFAULT_CENTER: [number, number] = [37.5407, -77.436] // Richmond, VA
const DEFAULT_ZOOM = 12

type GeocodedEvent = EventWithCoords & { latitude: number; longitude: number }

function MapController({ selectedEvent }: { selectedEvent?: GeocodedEvent | null }) {
  const map = useMap()

  useEffect(() => {
    if (selectedEvent?.latitude != null && selectedEvent?.longitude != null) {
      map.flyTo([selectedEvent.latitude, selectedEvent.longitude], 15, {
        duration: 1.2,
      })
    }
  }, [map, selectedEvent])

  return null
}

export function DispatchMap({
  events = [],
  selectedEventId = null,
  onSelectEvent,
  center = DEFAULT_CENTER,
  zoom = DEFAULT_ZOOM,
  className = 'dispatch-map-container',
}: DispatchMapProps) {
  const mappedEvents = useMemo(() => {
    return events.filter(
      (ev): ev is GeocodedEvent =>
        typeof ev.latitude === 'number' &&
        typeof ev.longitude === 'number' &&
        !Number.isNaN(ev.latitude) &&
        !Number.isNaN(ev.longitude),
    )
  }, [events])

  const selectedEvent = useMemo(() => {
    if (!selectedEventId) return null
    return mappedEvents.find((e) => e.id === selectedEventId) || null
  }, [mappedEvents, selectedEventId])

  return (
    <div className={className}>
      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={true}
        className="leaflet-map-root"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapController selectedEvent={selectedEvent} />

        {mappedEvents.map((event) => (
          <EventMarker
            key={event.id}
            event={event}
            isSelected={event.id === selectedEventId}
            onSelect={onSelectEvent}
          />
        ))}
      </MapContainer>
    </div>
  )
}
