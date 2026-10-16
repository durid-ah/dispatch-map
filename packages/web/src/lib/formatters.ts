/**
 * Date and category formatting utilities for dispatch events and responders.
 */

export function formatRelativeTime(dateString: string): string {
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

export function formatExactTime(dateString: string): string {
  try {
    const date = new Date(dateString)
    return date.toLocaleTimeString(undefined, {
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return dateString
  }
}

export function formatFullDateTime(dateString: string): string {
  try {
    const date = new Date(dateString)
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return dateString
  }
}

export function formatElapsedDuration(startIso: string, endIso: string): string {
  try {
    const start = new Date(startIso).getTime()
    const end = new Date(endIso).getTime()
    const diffSec = Math.max(0, Math.floor((end - start) / 1000))

    const mins = Math.floor(diffSec / 60)
    const secs = diffSec % 60

    if (mins === 0) {
      return `+${secs}s`
    }
    return `+${mins}m ${secs}s`
  } catch {
    return ''
  }
}

export function getCallCategoryVariant(
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
