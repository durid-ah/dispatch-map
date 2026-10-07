import { MapPin } from 'lucide-react'
import { Badge } from '@/components/ui/badge.tsx'
import { Card } from '@/components/ui/card.tsx'
import type { EventWithCoords } from '@/features/events/types/index.ts'
import { cn } from '@/lib/utils.ts'

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

function getCallCategoryVariant(
  callType: string,
): 'fire' | 'medical' | 'traffic' | 'police' {
  const lower = callType.toLowerCase()
  if (lower.includes('fire') || lower.includes('alarm') || lower.includes('smoke')) {
    return 'fire'
  }
  if (
    lower.includes('med') ||
    lower.includes('ems') ||
    lower.includes('cardiac') ||
    lower.includes('injury')
  ) {
    return 'medical'
  }
  if (
    lower.includes('traffic') ||
    lower.includes('accident') ||
    lower.includes('crash')
  ) {
    return 'traffic'
  }
  return 'police'
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
          className="max-w-[210px] truncate text-[11px] font-semibold tracking-wide"
        >
          {event.call_type}
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
        <span className="font-mono text-muted-foreground">#{event.id}</span>
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
