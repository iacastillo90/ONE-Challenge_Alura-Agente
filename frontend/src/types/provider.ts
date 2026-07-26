export interface Provider {
  name: string
  model: string
  priority: number
  available: boolean
  rate_limited: boolean
  degraded: boolean
}
