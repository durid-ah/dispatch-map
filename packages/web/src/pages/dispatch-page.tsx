import { useEffect, useMemo, useState } from 'react'
import { AppHeader } from '@/components/layout/app-header.tsx'
import { AppLayout } from '@/components/layout/app-layout.tsx'
import { useEventsQuery } from '@/features/events/api/use-events-query.ts'
import { EventList } from '@/features/events/components/event-list.tsx'
import type { EventWithCoords } from '@/features/events/types/index.ts'
import { DispatchMap } from '@/features/map/components/dispatch-map.tsx'

export function DispatchPage() {
  const [hours, setHours] = useState(24)
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null)

  const {
    data: events,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useEventsQuery({ hours })

  const selectedEvent = useMemo(() => {
    if (!selectedEventId) return null
    return events?.find((e) => e.id === selectedEventId) || null
  }, [events, selectedEventId])

  const handleSelectEvent = (event: EventWithCoords) => {
    setSelectedEventId(event.id)
  }

  const handleDeselectEvent = () => {
    setSelectedEventId(null)
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && selectedEventId !== null) {
        setSelectedEventId(null)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedEventId])

  const handleHoursChange = (newHours: number) => {
    setHours(newHours)
    setSelectedEventId(null)
  }

  const handleRefresh = () => {
    void refetch()
  }

  return (
    <AppLayout
      header={
        <AppHeader
          hours={hours}
          onHoursChange={handleHoursChange}
          isFetching={isFetching}
          onRefresh={handleRefresh}
          eventCount={events?.length}
        />
      }
    >
      <div className="flex flex-1 w-full h-full overflow-hidden flex-col-reverse md:flex-row">
        <EventList
          events={events}
          selectedEventId={selectedEventId}
          selectedEvent={selectedEvent}
          onSelectEvent={handleSelectEvent}
          onDeselectEvent={handleDeselectEvent}
          onCenterOnMap={handleSelectEvent}
          isLoading={isLoading}
          isError={isError}
          error={error}
          onRetry={handleRefresh}
        />
        <DispatchMap
          events={events}
          selectedEventId={selectedEventId}
          onSelectEvent={handleSelectEvent}
        />
      </div>
    </AppLayout>
  )
}
