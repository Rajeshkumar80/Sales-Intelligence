import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart3,
  Database,
  FolderDown,
  LayoutDashboard,
  Menu,
  Moon,
  ServerCog,
  Settings as SettingsIcon,
  Sun,
  Table2,
  Workflow,
  X,
} from 'lucide-react'
import { api } from '../api/client'
import type { Health } from '../api/types'
import { useTheme } from '../lib/theme'
import { Badge } from './ui'

const groups = [
  {
    label: 'Analyze',
    items: [
      { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
      { to: '/analytics', label: 'Sales Analytics', icon: BarChart3 },
      { to: '/transactions', label: 'Transactions', icon: Table2 },
    ],
  },
  {
    label: 'Pipeline',
    items: [
      { to: '/ingestion', label: 'Data Ingestion', icon: Database },
      { to: '/jobs', label: 'Hadoop Jobs', icon: Workflow },
      { to: '/hive', label: 'Hive Analytics', icon: ServerCog },
    ],
  },
  {
    label: 'Output',
    items: [
      { to: '/reports', label: 'Reports', icon: FolderDown },
      { to: '/settings', label: 'Settings', icon: SettingsIcon },
    ],
  },
]

const navigation = groups.flatMap((group) => group.items)

function HealthPill() {
  const { data, isError } = useQuery({
    queryKey: ['health'],
    queryFn: () => api<Health>('/api/health'),
    refetchInterval: 30_000,
  })
  if (isError) return <Badge tone="danger">API offline</Badge>
  if (!data) return <Badge tone="neutral">Checking…</Badge>
  return <Badge tone={data.status === 'ok' ? 'success' : 'warning'}>{data.status === 'ok' ? 'Services healthy' : 'Degraded'}</Badge>
}

export default function Layout() {
  const { theme, toggle } = useTheme()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  const current = navigation.find((item) => item.to === pathname)?.label ?? 'Overview'

  const links = (
    <nav className="flex flex-col gap-6">
      {groups.map((group) => (
        <div key={group.label}>
          <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400 dark:text-slate-600">
            {group.label}
          </p>
          <div className="flex flex-col gap-0.5">
            {group.items.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium transition ${
                    isActive
                      ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-200'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-slate-100'
                  }`
                }
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden />
                {label}
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </nav>
  )

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
      <aside className="hidden border-r border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 lg:block">
        <div className="mb-8 flex items-center gap-2.5 px-2 pt-2">
          <span className="h-2 w-2 rounded-full bg-brand-500" aria-hidden />
          <span className="text-[15px] font-semibold tracking-tight text-slate-900 dark:text-white">Sales Intelligence</span>
        </div>
        {links}
      </aside>

      <div className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90 lg:px-8">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="btn-secondary px-2.5 lg:hidden"
              onClick={() => setOpen((value) => !value)}
              aria-label="Toggle navigation"
            >
              {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
            <p className="text-[13px] font-medium text-slate-700 dark:text-slate-200">{current}</p>
          </div>
          <div className="flex items-center gap-2">
            <HealthPill />
            <button type="button" onClick={toggle} className="btn-secondary px-2.5" aria-label="Toggle theme">
              {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
          </div>
        </header>

        {open && (
          <div className="border-b border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 lg:hidden">{links}</div>
        )}

        <main className="flex-1 px-4 py-7 lg:px-9">
          <div className="mx-auto w-full max-w-[1500px]">
            <Outlet />
          </div>
        </main>

        <footer className="border-t border-slate-200 px-4 py-4 text-[11px] text-slate-500 dark:border-slate-800 dark:text-slate-500 lg:px-9">
          Single-node pseudo-distributed Hadoop (YARN containers). All timestamps stored in UTC and rendered in your local timezone.
        </footer>
      </div>
    </div>
  )
}
