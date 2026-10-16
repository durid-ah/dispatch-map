import {
  AlertTriangle,
  ArrowLeft,
  Clock,
  Crosshair,
  Loader2,
  MapPin,
  Shield,
  Users,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge.tsx'
import { Button } from '@/components/ui/button.tsx'
import { Card } from '@/components/ui/card.tsx'
import { ScrollArea } from '@/components/ui/scroll-area.tsx'
import { useEventRespondersQuery } from '@/features/events/api/use-event-responders-query.ts'
import { ResponderCard } from '@/features/events/components/responder-card.tsx'
import type { EventWithCoords } from '@/features/events/types/index.ts'
import {
  formatFullDateTime,
  formatRelativeTime,
  getCallCategoryVariant,
} from '@/lib/formatters.ts'
import { cn } from '@/lib/utils.ts'

export interface EventDetailCardProps {
  event: EventWithCoords
  onBack: () => void
  onCenterOnMap?: (event: EventWithCoords) => void
}

export function EventDetailCard({
  event,
  onBack,
  onCenterOnMap,
}: EventDetailCardProps) {
  const hasCoords = event.latitude !== null && event.longitude !== null
  const categoryVariant = getCallCategoryVariant(event.call_type)
  const relativeTime = formatRelativeTime(event.time_received)
  const fullDateTime = formatFullDateTime(event.time_received)

  const {
    data: respondersData,
    isLoading,
    isError,
    error,
    refetch,
  } = useEventRespondersQuery(event.external_id)

  const responders = respondersData?.responders ?? []

  return (
    <div className="w-full md:w-[390px] md:min-w-[320px] md:max-w-[440px] bg-card/40 border-r border-border flex flex-col h-full shrink-0 z-10">
      {/* Top Action Header */}
      <div className="p-3 border-b border-border flex items-center justify-between bg-card/70 backdrop-blur-xs">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onBack}
          className="text-xs h-8 px-2 font-medium text-muted-foreground hover:text-foreground -ml-1 gap-1.5"
          aria-label="Back to all calls"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>All calls</span>
        </Button>

        <span
          className="text-[11px] text-muted-foreground whitespace-nowrap font-medium"
          title={new Date(event.time_received).toLocaleString()}
        >
          {relativeTime}
        </span>
      </div>

      {/* Main Content Area */}
      <ScrollArea className="flex-1 px-3 py-3">
        <div className="space-y-4 pb-4">
          {/* Incident Overview Card */}
          <Card className="p-3.5 space-y-3 bg-card/70 border-border/80 shadow-xs">
            <div className="flex items-start justify-between gap-2">
              <Badge
                variant={categoryVariant}
                className="text-xs font-bold tracking-wide uppercase px-2.5 py-0.5"
              >
                {event.call_type}
              </Badge>
            </div>

            {/* Location */}
            <div className="space-y-1">
              <div className="flex items-start gap-1.5 text-xs text-muted-foreground">
                <MapPin className="h-4 w-4 shrink-0 mt-0.5 text-primary" />
                <span className="text-sm font-semibold text-foreground leading-snug break-words">
                  {event.location}
                </span>
              </div>
            </div>

            {/* Time Received */}
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground pt-1 border-t border-border/40">
              <Clock className="h-3.5 w-3.5 text-muted-foreground/70 shrink-0" />
              <span className="text-[11px] font-medium">{fullDateTime}</span>
            </div>

            {/* Coordinates / Map Action */}
            <div className="flex items-center justify-between pt-1 border-t border-border/40 text-xs gap-2">
              <Badge
                variant="outline"
                className={cn(
                  'text-[10px] font-mono px-2 py-0.5',
                  hasCoords
                    ? 'text-sky-400 border-sky-500/30 bg-sky-500/10'
                    : 'text-muted-foreground border-border',
                )}
              >
                {hasCoords
                  ? `📍 ${event.latitude?.toFixed(4)}, ${event.longitude?.toFixed(4)}`
                  : '⏳ Pending Geocoding'}
              </Badge>

              {hasCoords && onCenterOnMap && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => onCenterOnMap(event)}
                  className="h-6 text-[11px] px-2 text-primary hover:text-primary gap-1"
                >
                  <Crosshair className="h-3 w-3" />
                  <span>Locate</span>
                </Button>
              )}
            </div>
          </Card>

          {/* Responders Section */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between px-0.5">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground tracking-wide">
                <Users className="h-4 w-4 text-primary" />
                <span>Assigned Units</span>
              </div>

              {!isLoading && (
                <Badge
                  variant="outline"
                  className="text-[10px] font-mono px-1.5 py-0 border-border text-muted-foreground"
                >
                  {responders.length} {responders.length === 1 ? 'Unit' : 'Units'}
                </Badge>
              )}
            </div>

            {/* Loading State */}
            {isLoading && (
              <div className="flex flex-col items-center justify-center p-8 bg-card/40 rounded-lg border border-border/60 text-muted-foreground gap-2">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
                <p className="text-xs">Fetching responding units…</p>
              </div>
            )}

            {/* Error State */}
            {isError && !isLoading && (
              <div className="p-4 bg-destructive/10 border border-destructive/30 rounded-lg flex flex-col items-center text-center gap-2">
                <AlertTriangle className="h-6 w-6 text-destructive" />
                <p className="text-xs text-destructive-foreground">
                  {error?.message || 'Failed to load responding units'}
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => void refetch()}
                  className="text-xs h-7 px-3 mt-1"
                >
                  Retry
                </Button>
              </div>
            )}

            {/* Empty State */}
            {!isLoading && !isError && responders.length === 0 && (
              <div className="p-6 bg-card/30 border border-border/60 rounded-lg flex flex-col items-center text-center gap-2 text-muted-foreground">
                <Shield className="h-7 w-7 text-muted-foreground/40" />
                <p className="text-xs font-medium text-foreground/80">
                  No units dispatched
                </p>
                <p className="text-[11px] text-muted-foreground max-w-[240px]">
                  No emergency responder units have been assigned to this incident yet.
                </p>
              </div>
            )}

            {/* Responder Cards List */}
            {!isLoading && !isError && responders.length > 0 && (
              <div className="space-y-2">
                {responders.map((responder, idx) => (
                  <ResponderCard
                    key={`${responder.unit}-${responder.agency}-${idx}`}
                    responder={responder}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </ScrollArea>
    </div>
  )
}
