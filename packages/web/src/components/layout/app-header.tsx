import { RotateCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge.tsx'
import { Button } from '@/components/ui/button.tsx'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select.tsx'
import { cn } from '@/lib/utils.ts'

export interface AppHeaderProps {
  hours?: number
  onHoursChange?: (hours: number) => void
  isFetching?: boolean
  onRefresh?: () => void
  eventCount?: number
}

const TIME_OPTIONS = [
  { label: 'Past 6 Hours', value: 6 },
  { label: 'Past 12 Hours', value: 12 },
  { label: 'Past 24 Hours', value: 24 },
  { label: 'Past 48 Hours', value: 48 },
  { label: 'Past 7 Days', value: 168 },
]

export function AppHeader({
  hours = 24,
  onHoursChange,
  isFetching = false,
  onRefresh,
  eventCount,
}: AppHeaderProps) {
  return (
    <header className="flex items-center justify-between px-4 py-2.5 gap-4 bg-card/60 backdrop-blur-md border-b border-border">
      <div className="flex items-center gap-3.5">
        <div className="flex items-center gap-2.5">
          <span className="text-xl leading-none select-none" aria-hidden="true">
            🚨
          </span>
          <div className="flex flex-col">
            <h1 className="text-sm font-bold tracking-tight text-foreground leading-tight">
              Richmond 911 Dispatch
            </h1>
            <span className="text-[11px] font-medium text-muted-foreground leading-tight">
              Active Emergency CAD Calls
            </span>
          </div>
        </div>

        <Badge
          variant="outline"
          className="gap-1.5 border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-emerald-400"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_6px_#22c55e] animate-pulse" />
          <span className="text-[10px] font-bold tracking-wider">LIVE</span>
        </Badge>
      </div>

      <div className="flex items-center gap-3">
        {eventCount !== undefined && (
          <Badge
            variant="secondary"
            className="gap-1.5 px-2.5 py-1 font-mono text-xs border border-border bg-card/80"
          >
            <span className="font-bold text-sky-400">{eventCount}</span>
            <span className="text-[10px] uppercase font-semibold text-muted-foreground">
              Calls
            </span>
          </Badge>
        )}

        <div className="flex items-center gap-2">
          <Select
            value={String(hours)}
            onValueChange={(val) => onHoursChange?.(Number(val))}
          >
            <SelectTrigger
              className="w-[145px] h-8 text-xs bg-card border-border"
              aria-label="Time Range"
            >
              <SelectValue placeholder="Select range" />
            </SelectTrigger>
            <SelectContent align="end">
              {TIME_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={String(opt.value)}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {onRefresh && (
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="h-8 w-8 bg-card border-border text-muted-foreground hover:text-foreground"
              onClick={onRefresh}
              disabled={isFetching}
              title="Refresh data"
              aria-label="Refresh data"
            >
              <RotateCw
                className={cn(
                  'h-3.5 w-3.5 transition-transform',
                  isFetching && 'animate-spin text-primary',
                )}
              />
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}
