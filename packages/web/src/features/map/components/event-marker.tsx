import { useEffect, useMemo, useRef } from 'react'
import L from 'leaflet'
import { Marker, Popup } from 'react-leaflet'
import type { EventWithCoords } from '@/features/events/types/index.ts'

export interface EventMarkerProps {
  event: EventWithCoords & { latitude: number; longitude: number }
  isSelected?: boolean
  onSelect?: (event: EventWithCoords) => void
}

function getCategoryInfo(callType: string): { color: string; category: string } {
  const lower = callType.toLowerCase()
  if (lower.includes('fire') || lower.includes('alarm') || lower.includes('smoke')) {
    return { color: '#ef4444', category: 'fire' }
  }
  if (lower.includes('med') || lower.includes('ems') || lower.includes('cardiac') || lower.includes('injury')) {
    return { color: '#10b981', category: 'medical' }
  }
  if (lower.includes('traffic') || lower.includes('accident') || lower.includes('crash')) {
    return { color: '#f59e0b', category: 'traffic' }
  }
  return { color: '#3b82f6', category: 'police' }
}

function createMarkerIcon(callType: string, isSelected: boolean): L.DivIcon {
  const { color, category } = getCategoryInfo(callType)
  const selectedClass = isSelected ? 'marker-selected' : ''

  return L.divIcon({
    className: `dispatch-marker-wrapper ${selectedClass}`,
    html: `
      <div class="dispatch-marker-pin marker-${category}">
        <span class="marker-pulse" style="--pulse-color: ${color};"></span>
        <span class="marker-dot" style="background-color: ${color};"></span>
      </div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -14],
  })
}

export function EventMarker({ event, isSelected = false, onSelect }: EventMarkerProps) {
  const markerRef = useRef<L.Marker | null>(null)
  const { category } = getCategoryInfo(event.call_type)

  const icon = useMemo(
    () => createMarkerIcon(event.call_type, isSelected),
    [event.call_type, isSelected],
  )

  useEffect(() => {
    if (isSelected && markerRef.current) {
      markerRef.current.openPopup()
    }
  }, [isSelected])

  return (
    <Marker
      ref={markerRef}
      position={[event.latitude, event.longitude]}
      icon={icon}
      eventHandlers={{
        click: () => onSelect?.(event),
      }}
    >
      <Popup className="dispatch-leaflet-popup">
        <div className="popup-body">
          <div className="popup-badge-row">
            <span className={`event-call-badge badge-${category}`}>
              {event.call_type}
            </span>
            <span className="popup-external-id">#{event.external_id}</span>
          </div>

          <p className="popup-location-text">{event.location}</p>

          <div className="popup-meta-row">
            <span>
              🕒 {new Date(event.time_received).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>
        </div>
      </Popup>
    </Marker>
  )
}
