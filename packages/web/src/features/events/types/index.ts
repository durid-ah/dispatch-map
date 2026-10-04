export interface EventWithCoords {
  id: number
  external_id: string
  time_received: string
  call_type: string
  location: string
  location_id: number | null
  latitude: number | null
  longitude: number | null
  created_at: string
  updated_at: string
}
