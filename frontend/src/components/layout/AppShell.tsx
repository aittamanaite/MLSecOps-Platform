import type { ReactNode } from 'react'
import { IconRail } from './IconRail'
import { StatusBar } from './StatusBar'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen bg-base">
      <IconRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <StatusBar />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}
