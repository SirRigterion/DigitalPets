import React from 'react'
import { cn } from '@shared/lib/utils'
import { PET_ACTIONS } from '@shared/config/constants'
import type { PetAction } from '@shared/types'
import { usePetActions, formatCooldown } from '@features/feed-pet/model/usePetActions'

interface ActionButtonProps {
  action: PetAction
  onClick: () => void
  disabled: boolean
  onCooldown: boolean
  cooldownRemaining: number
  cooldownProgress: number  // 0-100
}

const ActionButton: React.FC<ActionButtonProps> = ({
  action,
  onClick,
  disabled,
  onCooldown,
  cooldownRemaining,
  cooldownProgress,
}) => {
  const isDisabled = disabled || onCooldown

  // Цвет прогресс-бара по типу действия
  const progressColor: Record<PetAction['type'], string> = {
    feed:  'bg-amber-400',
    play:  'bg-green-400',
    heal:  'bg-red-400',
    clean: 'bg-cyan-400',
  }

  const glowColor: Record<PetAction['type'], string> = {
    feed:  'hover:shadow-amber-500/20',
    play:  'hover:shadow-green-500/20',
    heal:  'hover:shadow-red-500/20',
    clean: 'hover:shadow-cyan-500/20',
  }

  return (
    <button
      onClick={onClick}
      disabled={isDisabled}
      className={cn(
        'relative flex flex-col items-center gap-1.5 pt-3 pb-2 px-2 rounded-2xl transition-all duration-200 font-body group overflow-hidden',
        'border',
        isDisabled
          ? 'opacity-50 cursor-not-allowed bg-white/3 border-white/8'
          : cn(
            'bg-white/8 border-white/12 cursor-pointer',
            'hover:bg-white/15 hover:border-white/25 hover:shadow-lg hover:-translate-y-0.5',
            glowColor[action.type],
            'active:scale-95 active:translate-y-0'
          )
      )}
      title={action.description}
    >
      {/* Иконка */}
      <span className={cn(
        'text-2xl transition-transform duration-200',
        !isDisabled && 'group-hover:scale-110 group-active:scale-90',
        onCooldown && 'opacity-40'
      )}>
        {action.emoji}
      </span>

      {/* Название */}
      <span className={cn(
        'text-xs font-semibold whitespace-nowrap transition-colors',
        isDisabled ? 'text-white/30' : 'text-white/70 group-hover:text-white/90'
      )}>
        {action.label}
      </span>

      {/* Таймер кулдауна */}
      {onCooldown && cooldownRemaining > 0 && (
        <span className="text-xs font-mono text-white/40 leading-none">
          {formatCooldown(cooldownRemaining)}
        </span>
      )}

      {/* Готово */}
      {!onCooldown && !disabled && action.cooldown > 0 && (
        <span className="text-xs text-white/25 leading-none">готово</span>
      )}

      {/* Прогресс-бар снизу */}
      {action.cooldown > 0 && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-white/5 rounded-b-2xl overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-all duration-1000',
              onCooldown ? progressColor[action.type] : 'bg-transparent'
            )}
            style={{ width: onCooldown ? `${cooldownProgress}%` : '0%' }}
          />
        </div>
      )}
    </button>
  )
}

interface ActionBarProps {
  isSleeping: boolean
  className?: string
}

export const ActionBar: React.FC<ActionBarProps> = ({ isSleeping, className }) => {
  const {
    executeAction,
    isOnCooldown,
    getCooldownRemaining,
    getCooldownProgress,
  } = usePetActions()

  return (
    <div className={cn('space-y-3', className)}>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {PET_ACTIONS.map((action) => {
          const onCooldown = isOnCooldown(action.type)
          const remaining  = getCooldownRemaining(action.type)
          const progress   = getCooldownProgress(action.type)

          return (
            <ActionButton
              key={action.id}
              action={action}
              onClick={() => executeAction(action.type)}
              disabled={isSleeping}
              onCooldown={onCooldown}
              cooldownRemaining={remaining}
              cooldownProgress={progress}
            />
          )
        })}
      </div>
    </div>
  )
}
