import React from 'react'
import type { PetStats } from '@shared/types'
import { cn, getStatBgColor } from '@shared/lib/utils'

interface StatBarProps {
  label: string
  emoji: string
  value: number
  max?: number
}

const StatBar: React.FC<StatBarProps> = ({ label, emoji, value, max = 100 }) => {
  const pct = Math.round((value / max) * 100)
  const colorClass = getStatBgColor(pct)

  return (
    <div className="flex items-center gap-3">
      <span className="text-xl w-7 shrink-0">{emoji}</span>
      <div className="flex-1 min-w-0">
        <div className="flex justify-between mb-1">
          <span className="text-xs font-bold font-body text-white/80 uppercase tracking-wider">{label}</span>
          <span className="text-xs font-mono text-white/60">{pct}%</span>
        </div>
        <div className="h-2.5 bg-white/10 rounded-full overflow-hidden">
          <div
            className={cn('h-full rounded-full transition-all duration-700 ease-out', colorClass)}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  )
}

interface StatsPanelProps {
  stats: PetStats
  className?: string
}

export const StatsPanel: React.FC<StatsPanelProps> = ({ stats, className }) => {
  return (
    <div className={cn('space-y-3 h-full', className)}>
      <StatBar label="Сытость" emoji="🍖" value={stats.hunger} />
      <StatBar label="Энергия" emoji="⚡" value={stats.energy} />
      <StatBar label="Настроение" emoji="😊" value={stats.happiness} />
      <StatBar label="Здоровье" emoji="❤️" value={stats.health} />
      <StatBar label="Чистота" emoji="✨" value={stats.cleanliness} />
    </div>
  )
}
