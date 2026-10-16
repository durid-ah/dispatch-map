import { MapPin } from 'lucide-react'
import { Badge } from '@/components/ui/badge.tsx'
import { Card } from '@/components/ui/card.tsx'
import type { EventWithCoords } from '@/features/events/types/index.ts'
import { formatRelativeTime, getCallCategoryVariant } from '@/lib/formatters.ts'
import { cn } from '@/lib/utils.ts'

export interface EventCardProps {
  event: EventWithCoords
  isSelected?: boolean
  onSelect?: (event: EventWithCoords) => void
}

export function EventCard({
  event,
  isSelected = false,
  onSelect,
}: EventCardProps) {
  const hasCoords = event.latitude !== null && event.longitude !== null
  const relativeTime = formatRelativeTime(event.time_received)
  const categoryVariant = getCallCategoryVariant(event.call_type)

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
    <Card
      role="button"
      tabIndex={0}
      aria-pressed={isSelected}
      data-event-id={event.id}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        'cursor-pointer p-3 transition-all hover:bg-accent/40 hover:border-slate-600 space-y-2 select-none border-border/70',
        isSelected &&
          'bg-accent/70 border-primary ring-1 ring-primary shadow-sm',
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <Badge
          variant={categoryVariant}
          className="max-w-[210px] min-w-0 text-[11px] font-semibold tracking-wide"
        >
          <span className="truncate" title={event.call_type}>
            {event.call_type}
          </span>
        </Badge>
        <span
          className="text-[11px] text-muted-foreground whitespace-nowrap"
          title={new Date(event.time_received).toLocaleString()}
        >
          {relativeTime}
        </span>
      </div>

      <div className="flex items-start gap-1.5 text-xs text-muted-foreground">
        <MapPin className="h-3.5 w-3.5 shrink-0 mt-0.5 text-muted-foreground/80" />
        <span className="break-words text-foreground/90 font-medium leading-snug">
          {event.location}
        </span>
      </div>

      <div className="flex items-center justify-between pt-1 border-t border-border/50 text-[10px]">
        <Badge
          variant="outline"
          className={cn(
            'text-[10px] px-1.5 py-0 font-medium',
            hasCoords
              ? 'text-sky-400 border-sky-500/30 bg-sky-500/10'
              : 'text-muted-foreground/80 border-border',
          )}
        >
          {hasCoords ? '📍 Mapped' : '⏳ Pending'}
        </Badge>
      </div>
    </Card>
  )
}
