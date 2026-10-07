import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils.ts'

// oxlint-disable-next-line react/only-export-components
export const badgeVariants = cva(
  'inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-primary text-primary-foreground shadow hover:bg-primary/80',
        secondary:
          'border-border bg-card text-secondary-foreground hover:bg-card/80',
        destructive:
          'border-transparent bg-destructive text-destructive-foreground shadow hover:bg-destructive/80',
        outline: 'border-border text-foreground',
        fire: 'border-red-500/35 bg-red-500/15 text-red-400 font-medium',
        medical: 'border-emerald-500/35 bg-emerald-500/15 text-emerald-400 font-medium',
        traffic: 'border-amber-500/35 bg-amber-500/15 text-amber-400 font-medium',
        police: 'border-blue-500/35 bg-blue-500/15 text-blue-400 font-medium',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}
