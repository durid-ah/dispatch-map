import { LoadingSpinner } from '@/components/common/loading-spinner.tsx'

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
    <header className="app-header">
      <div className="app-header-left">
        <div className="app-header-brand">
          <span className="app-header-icon" aria-hidden="true">
            🚨
          </span>
          <div className="app-header-titles">
            <h1 className="app-header-title">Richmond 911 Dispatch</h1>
            <span className="app-header-subtitle">Active Emergency CAD Calls</span>
          </div>
        </div>

        <div className="app-header-live-badge">
          <span className="live-pulse-dot" />
          <span className="live-pulse-text">LIVE</span>
        </div>
      </div>

      <div className="app-header-right">
        {eventCount !== undefined && (
          <div className="app-header-count">
            <span className="count-number">{eventCount}</span>
            <span className="count-label">Calls</span>
          </div>
        )}

        <div className="app-header-controls">
          <label htmlFor="time-range-select" className="sr-only">
            Time Range
          </label>
          <select
            id="time-range-select"
            className="app-header-select"
            value={hours}
            onChange={(e) => onHoursChange?.(Number(e.target.value))}
          >
            {TIME_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          {onRefresh && (
            <button
              type="button"
              className="app-header-refresh-btn"
              onClick={onRefresh}
              disabled={isFetching}
              title="Refresh data"
              aria-label="Refresh data"
            >
              {isFetching ? (
                <LoadingSpinner size="sm" label="Refreshing..." />
              ) : (
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                </svg>
              )}
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
