import { useMemo, useState } from 'react'
import { LoadingSpinner } from '@/components/common/loading-spinner.tsx'
import { EventCard } from '@/features/events/components/event-card.tsx'
import type { EventWithCoords } from '@/features/events/types/index.ts'

export interface EventListProps {
  events?: EventWithCoords[]
  selectedEventId?: number | null
  onSelectEvent?: (event: EventWithCoords) => void
  isLoading?: boolean
  isError?: boolean
  error?: Error | null
  onRetry?: () => void
}

export function EventList({
  events = [],
  selectedEventId = null,
  onSelectEvent,
  isLoading = false,
  isError = false,
  error = null,
  onRetry,
}: EventListProps) {
  const [searchQuery, setSearchQuery] = useState('')

  const filteredEvents = useMemo(() => {
    if (!searchQuery.trim()) {
      return events
    }
    const query = searchQuery.toLowerCase().trim()
    return events.filter(
      (ev) =>
        ev.call_type.toLowerCase().includes(query) ||
        ev.location.toLowerCase().includes(query) ||
        ev.external_id.toLowerCase().includes(query),
    )
  }, [events, searchQuery])

  return (
    <div className="event-list-pane">
      <div className="event-list-header">
        <div className="event-search-wrapper">
          <svg
            className="search-icon"
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
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            type="search"
            className="event-search-input"
            placeholder="Search by call type, address, ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search dispatch events"
          />
          {searchQuery && (
            <button
              type="button"
              className="event-search-clear"
              onClick={() => setSearchQuery('')}
              aria-label="Clear search"
            >
              ×
            </button>
          )}
        </div>

        <div className="event-list-stats">
          <span>
            {searchQuery
              ? `${filteredEvents.length} of ${events.length} calls`
              : `${events.length} calls recorded`}
          </span>
        </div>
      </div>

      <div className="event-list-content">
        {isLoading && (
          <div className="event-list-status">
            <LoadingSpinner size="lg" label="Loading dispatch calls..." />
            <p className="status-text">Fetching dispatch events...</p>
          </div>
        )}

        {isError && !isLoading && (
          <div className="event-list-status error">
            <span className="status-icon" aria-hidden="true">⚠️</span>
            <p className="status-text">
              {error?.message || 'Failed to load dispatch events'}
            </p>
            {onRetry && (
              <button
                type="button"
                className="event-list-retry-btn"
                onClick={onRetry}
              >
                Retry
              </button>
            )}
          </div>
        )}

        {!isLoading && !isError && filteredEvents.length === 0 && (
          <div className="event-list-status empty">
            <span className="status-icon" aria-hidden="true">📋</span>
            <p className="status-text">
              {searchQuery
                ? `No calls matching "${searchQuery}"`
                : 'No incidents recorded in this timeframe'}
            </p>
          </div>
        )}

        {!isLoading && !isError && filteredEvents.length > 0 && (
          <div className="event-card-container">
            {filteredEvents.map((event) => (
              <EventCard
                key={event.id}
                event={event}
                isSelected={event.id === selectedEventId}
                onSelect={onSelectEvent}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
