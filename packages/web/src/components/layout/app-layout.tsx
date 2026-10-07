import type { ReactNode } from 'react'

export interface AppLayoutProps {
  header?: ReactNode
  children: ReactNode
}

export function AppLayout({ header, children }: AppLayoutProps) {
  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-background text-foreground">
      {header && <div className="shrink-0 z-20">{header}</div>}
      <main className="flex-1 min-h-0 flex overflow-hidden relative">{children}</main>
    </div>
  )
}
