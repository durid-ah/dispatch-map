import { useMemo } from 'react'
import { CheckCircle2, Clock, Navigation, Radio, Shield } from 'lucide-react'
import { Badge } from '@/components/ui/badge.tsx'
import { Card } from '@/components/ui/card.tsx'
import type { ResponderRead } from '@/features/events/types/index.ts'
import { formatElapsedDuration, formatExactTime } from '@/lib/formatters.ts'
import { cn } from '@/lib/utils.ts'

export interface ResponderCardProps {
  responder: ResponderRead
}

function getStatusBadgeStyle(status: string): {
  variantClasses: string
  icon: typeof Radio
} {
  const upper = status.toUpperCase()
  if (upper === 'ARRIVED') {
    return {
      variantClasses: 'border-emerald-500/40 bg-emerald-500/15 text-emerald-400',
      icon: CheckCircle2,
    }
  }
  if (upper === 'ENROUTE') {
    return {
      variantClasses: 'border-amber-500/40 bg-amber-500/15 text-amber-400',
      icon: Navigation,
    }
  }
  if (upper === 'DISPATCHED') {
    return {
      variantClasses: 'border-sky-500/40 bg-sky-500/15 text-sky-400',
      icon: Radio,
    }
  }
  return {
    variantClasses: 'border-border bg-muted/30 text-muted-foreground',
    icon: Clock,
  }
}

export function ResponderCard({ responder }: ResponderCardProps) {
  const sortedStatuses = useMemo(() => {
    return [...responder.statuses].sort((a, b) => {
      if (a.status_order !== b.status_order) {
        return a.status_order - b.status_order
      }
      return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    })
  }, [responder.statuses])

  const latestStatus = sortedStatuses.length > 0 ? sortedStatuses[sortedStatuses.length - 1] : null
  const currentStatusName = latestStatus?.status ?? 'ASSIGNED'
  const { variantClasses, icon: StatusIcon } = getStatusBadgeStyle(currentStatusName)

  return (
    <Card className="p-3 bg-card/60 border-border/80 shadow-xs space-y-3">
      {/* Unit Header */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          <Badge
            variant="outline"
            className="font-mono font-bold text-xs tracking-wider border-primary/30 bg-primary/10 text-primary px-2 py-0.5"
          >
            {responder.unit}
          </Badge>
          <Badge
            variant="secondary"
            className="text-[10px] uppercase font-semibold text-muted-foreground bg-muted/60 px-1.5 py-0"
          >
            {responder.agency}
          </Badge>
          {responder.dispatch_area && (
            <Badge
              variant="outline"
              className="text-[10px] uppercase text-muted-foreground/80 border-border px-1.5 py-0"
            >
              {responder.dispatch_area}
            </Badge>
          )}
        </div>

        <Badge
          variant="outline"
          className={cn(
            'text-[10px] font-semibold tracking-wide flex items-center gap-1 px-2 py-0.5 shrink-0',
            variantClasses,
          )}
        >
          <StatusIcon className="h-3 w-3" />
          <span>{currentStatusName}</span>
        </Badge>
      </div>

      {/* Chronological Status Stepper */}
      {sortedStatuses.length > 0 ? (
        <div className="pt-1 border-t border-border/50">
          <div className="text-[10px] uppercase font-semibold text-muted-foreground/70 mb-2 tracking-wider flex items-center gap-1">
            <Clock className="h-3 w-3 text-muted-foreground/60" />
            <span>Status Timeline</span>
          </div>

          <div className="space-y-0 relative pl-3">
            {sortedStatuses.map((statusItem, idx) => {
              const isLast = idx === sortedStatuses.length - 1
              const elapsed = idx > 0
                ? formatElapsedDuration(sortedStatuses[idx - 1].created_at, statusItem.created_at)
                : null

              return (
                <div key={`${statusItem.status}-${statusItem.status_order}-${idx}`} className="relative pb-3 last:pb-0">
                  {/* Vertical line connecting nodes */}
                  {!isLast && (
                    <div className="absolute left-[-7px] top-[7px] bottom-0 w-[1.5px] bg-border" />
                  )}

                  {/* Timeline dot */}
                  <div
                    className={cn(
                      'absolute left-[-11px] top-[3px] rounded-full flex items-center justify-center',
                      isLast
                        ? 'h-2.5 w-2.5 bg-primary ring-2 ring-primary/40 ring-offset-1 ring-offset-card'
                        : 'h-2 w-2 bg-muted-foreground/50',
                    )}
                  />

                  {/* Status Item Details */}
                  <div className="flex items-center justify-between text-xs gap-2">
                    <span
                      className={cn(
                        'font-medium text-[11px] tracking-wide',
                        isLast ? 'text-foreground font-semibold' : 'text-muted-foreground',
                      )}
                    >
                      {statusItem.status}
                    </span>

                    <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground shrink-0">
                      {elapsed && (
                        <span className="font-mono text-[9px] px-1 py-0.2 rounded bg-muted/50 text-muted-foreground/90 border border-border/50">
                          {elapsed}
                        </span>
                      )}
                      <span className="font-mono text-muted-foreground/80">
                        {formatExactTime(statusItem.created_at)}
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground/70 italic pt-1 border-t border-border/40">
          <Shield className="h-3.5 w-3.5" />
          <span>No status progression recorded</span>
        </div>
      )}
    </Card>
  )
}
