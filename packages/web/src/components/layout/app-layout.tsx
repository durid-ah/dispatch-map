import type { ReactNode } from 'react'

export interface AppLayoutProps {
  header?: ReactNode
  children: ReactNode
}

export function AppLayout({ header, children }: AppLayoutProps) {
  return (
    <div className="app-layout">
      {header && <div className="app-layout-header">{header}</div>}
      <main className="app-layout-main">{children}</main>
    </div>
  )
}
