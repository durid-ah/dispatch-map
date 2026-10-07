import { useMemo, useState } from 'react'
import { AlertTriangle, Inbox, Loader2, Search, X } from 'lucide-react'
import { Button } from '@/components/ui/button.tsx'
import { Input } from '@/components/ui/input.tsx'
import { ScrollArea } from '@/components/ui/scroll-area.tsx'
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
        ev.location.toLowerCase().includes(query),
    )
  }, [events, searchQuery])

  return (
    <div className="w-full md:w-[390px] md:min-w-[320px] md:max-w-[440px] bg-card/40 border-r border-border flex flex-col h-full shrink-0 z-10">
      <div className="p-3 border-b border-border flex flex-col gap-2 bg-card/60">
        <div className="relative flex items-center">
          <Search className="absolute left-2.5 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
          <Input
            type="search"
            className="pl-8 pr-8 h-8 text-xs bg-card border-border"
            placeholder="Search by call type, address, ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search dispatch events"
          />
          {searchQuery && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="absolute right-1 h-6 w-6 text-muted-foreground hover:text-foreground"
              onClick={() => setSearchQuery('')}
              aria-label="Clear search"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>

        <div className="text-[11px] text-muted-foreground font-medium pl-0.5">
          {searchQuery
            ? `${filteredEvents.length} of ${events.length} calls`
            : `${events.length} calls recorded`}
        </div>
      </div>

      <div className="flex-1 min-h-0 flex flex-col">
        {isLoading && (
          <div className="flex flex-col items-center justify-center p-12 text-center text-muted-foreground gap-2">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-xs">Fetching dispatch events...</p>
          </div>
        )}

        {isError && !isLoading && (
          <div className="flex flex-col items-center justify-center p-8 text-center text-muted-foreground gap-2">
            <AlertTriangle className="h-8 w-8 text-destructive" />
            <p className="text-xs text-destructive-foreground">
              {error?.message || 'Failed to load dispatch events'}
            </p>
            {onRetry && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="mt-2 text-xs h-7"
                onClick={onRetry}
              >
                Retry
              </Button>
            )}
          </div>
        )}

        {!isLoading && !isError && filteredEvents.length === 0 && (
          <div className="flex flex-col items-center justify-center p-12 text-center text-muted-foreground gap-2">
            <Inbox className="h-8 w-8 text-muted-foreground/50" />
            <p className="text-xs">
              {searchQuery
                ? `No calls matching "${searchQuery}"`
                : 'No incidents recorded in this timeframe'}
            </p>
          </div>
        )}

        {!isLoading && !isError && filteredEvents.length > 0 && (
          <ScrollArea className="flex-1 px-3 py-2">
            <div className="flex flex-col gap-2 pb-2">
              {filteredEvents.map((event) => (
                <EventCard
                  key={event.id}
                  event={event}
                  isSelected={event.id === selectedEventId}
                  onSelect={onSelectEvent}
                />
              ))}
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  )
}
