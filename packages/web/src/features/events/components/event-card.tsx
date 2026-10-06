import type { EventWithCoords } from '@/features/events/types/index.ts'

export interface EventCardProps {
  event: EventWithCoords
  isSelected?: boolean
  onSelect?: (event: EventWithCoords) => void
}

function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString)
    const now = new Date()
    const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

    if (diffSeconds < 0) {
      return 'Just now'
    }
    if (diffSeconds < 60) {
      return `${diffSeconds}s ago`
    }
    const diffMinutes = Math.floor(diffSeconds / 60)
    if (diffMinutes < 60) {
      return `${diffMinutes}m ago`
    }
    const diffHours = Math.floor(diffMinutes / 60)
    if (diffHours < 24) {
      return `${diffHours}h ago`
    }
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}d ago`
  } catch {
    return dateString
  }
}

function getCallCategoryClass(callType: string): string {
  const lower = callType.toLowerCase()
  if (lower.includes('fire') || lower.includes('alarm') || lower.includes('smoke')) {
    return 'badge-fire'
  }
  if (lower.includes('med') || lower.includes('ems') || lower.includes('cardiac') || lower.includes('injury')) {
    return 'badge-medical'
  }
  if (lower.includes('traffic') || lower.includes('accident') || lower.includes('crash')) {
    return 'badge-traffic'
  }
  return 'badge-police'
}

export function EventCard({ event, isSelected = false, onSelect }: EventCardProps) {
  const hasCoords = event.latitude !== null && event.longitude !== null
  const relativeTime = formatRelativeTime(event.time_received)
  const categoryClass = getCallCategoryClass(event.call_type)

  const handleClick = () => {
    onSelect?.(event)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onSelect?.(event)
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-pressed={isSelected}
      className={`event-card ${isSelected ? 'selected' : ''}`.trim()}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      data-event-id={event.id}
    >
      <div className="event-card-header">
        <span className={`event-call-badge ${categoryClass}`}>
          {event.call_type}
        </span>
        <span className="event-time" title={new Date(event.time_received).toLocaleString()}>
          {relativeTime}
        </span>
      </div>

      <div className="event-card-location">
        <svg
          className="location-icon"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
          <circle cx="12" cy="10" r="3" />
        </svg>
        <span className="location-text">{event.location}</span>
      </div>

      <div className="event-card-footer">
        <span className={`event-coords-badge ${hasCoords ? 'mapped' : 'unmapped'}`}>
          {hasCoords ? '📍 Mapped' : '⏳ Pending'}
        </span>
      </div>
    </div>
  )
}
