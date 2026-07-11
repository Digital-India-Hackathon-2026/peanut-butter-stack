import type { ReactNode } from 'react'
import { motion } from 'framer-motion'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="app-shell">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        className="app-shell-inner"
      >
        {children}
      </motion.div>
    </div>
  )
}
