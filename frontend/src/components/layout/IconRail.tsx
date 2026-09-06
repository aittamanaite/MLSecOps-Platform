import { NavLink } from 'react-router-dom'
import type { ReactNode } from 'react'

interface NavItem {
  to: string
  label: string
  icon: ReactNode
}

function Icon({ path }: { path: string }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d={path} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: <Icon path="M4 13h6V4H4v9zm0 7h6v-5H4v5zm10 0h6V11h-6v9zm0-16v5h6V4h-6z" /> },
  { to: '/inspect', label: 'Inspector', icon: <Icon path="M9 20l-5.5-5.5m2.5-4.5a7 7 0 1 1 14 0 7 7 0 0 1-14 0z" /> },
  { to: '/batch', label: 'Batch', icon: <Icon path="M4 4h16v6H4V4zm0 10h16v6H4v-6zm3-7h.01M7 17h.01" /> },
  { to: '/alerts', label: 'Alerts', icon: <Icon path="M12 3l9 16H3l9-16zm0 6v4m0 3h.01" /> },
  { to: '/status', label: 'Status', icon: <Icon path="M3 12h4l3 8 4-16 3 8h4" /> },
]

const SETTINGS_ITEM: NavItem = {
  to: '/settings',
  label: 'Settings',
  icon: (
    <Icon path="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm7-3a7 7 0 0 0-.1-1.2l2-1.6-2-3.4-2.4.6a7 7 0 0 0-2-1.2L14 2h-4l-.5 2.6a7 7 0 0 0-2 1.2l-2.4-.6-2 3.4 2 1.6A7 7 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.6 2 3.4 2.4-.6a7 7 0 0 0 2 1.2L10 22h4l.5-2.6a7 7 0 0 0 2-1.2l2.4.6 2-3.4-2-1.6c.1-.4.1-.8.1-1.2z" />
  ),
}

function NavIcon({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.to}
      title={item.label}
      className={({ isActive }) =>
        `group relative flex h-11 w-11 items-center justify-center rounded-input transition-colors duration-150 ${
          isActive ? 'text-primary' : 'text-secondary hover:text-primary'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <span className="absolute left-0 top-1/2 h-6 w-[3px] -translate-y-1/2 rounded-full bg-accent" />
          )}
          {item.icon}
        </>
      )}
    </NavLink>
  )
}

/** Fixed 72px icon rail, left side (§8.1). Settings pinned to bottom. */
export function IconRail() {
  return (
    <nav className="flex h-full w-[72px] shrink-0 flex-col items-center justify-between border-r border-hairline bg-panel py-4">
      <div className="flex flex-col items-center gap-2">
        {NAV_ITEMS.map((item) => (
          <NavIcon key={item.to} item={item} />
        ))}
      </div>
      <NavIcon item={SETTINGS_ITEM} />
    </nav>
  )
}
