import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merges conditional class names using `clsx` and resolves conflicting
 * Tailwind CSS utility classes using `tailwind-merge`.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
