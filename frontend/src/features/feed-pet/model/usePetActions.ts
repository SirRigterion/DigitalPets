import { useState, useCallback, useEffect } from 'react'
import { usePetStore } from '@entities/pet'
import { PET_ACTIONS } from '@shared/config/constants'
import type {PetAction, PetStatsDelta} from '@shared/types'

const STORAGE_KEY    = 'digital-pet-cooldowns'
const POLL_INTERVAL  = 15 * 60 * 1000  // 15 минут — получаем статы с сервера
const TICK_INTERVAL  = 1_000           // 1 секунда — обновляем таймеры в UI

export function formatCooldown(seconds: number): string {
  if (seconds <= 0) return ''
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return m > 0 ? `${h}ч ${m}м` : `${h}ч`
  if (m > 0) return s > 0 ? `${m}м ${s}с` : `${m}м`
  return `${s}с`
}

function loadCooldowns(): Record<string, number> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as Record<string, number>
    const now = Date.now()
    return Object.fromEntries(Object.entries(parsed).filter(([, end]) => end > now))
  } catch {
    return {}
  }
}

function saveCooldowns(cooldowns: Record<string, number>) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(cooldowns)) } catch {}
}

interface UsePetActionsReturn {
  executeAction:        (actionType: PetAction['type']) => void
  isOnCooldown:         (actionType: PetAction['type']) => boolean
  getCooldownRemaining: (actionType: PetAction['type']) => number
  getCooldownProgress:  (actionType: PetAction['type']) => number
  lastActionMessage:    string | null
}

export function usePetActions(): UsePetActionsReturn {
  const { pet, applyStatChanges, updatePhrase, fetchPet } = usePetStore()

  const [cooldowns, setCooldowns]                 = useState<Record<string, number>>(() => loadCooldowns())
  const [lastActionMessage, setLastActionMessage] = useState<string | null>(null)
  const [, setTick]                               = useState(0)

  // ── Интервал 1: секундный тик — обновляет таймеры кулдаунов в UI ──────────
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), TICK_INTERVAL)
    return () => clearInterval(id)
  }, [])

  // ── Интервал 2: поллинг статов с сервера каждые 15 минут ─────────────────
  useEffect(() => {
    const id = setInterval(() => fetchPet(), POLL_INTERVAL)
    return () => clearInterval(id)
  }, [fetchPet])

  const isOnCooldown = useCallback(
    (actionType: PetAction['type']) => {
      const end = cooldowns[actionType]
      return !!end && Date.now() < end
    },
    [cooldowns]
  )

  const getCooldownRemaining = useCallback(
    (actionType: PetAction['type']) => {
      const end = cooldowns[actionType]
      if (!end) return 0
      return Math.max(0, Math.ceil((end - Date.now()) / 1000))
    },
    [cooldowns]
  )

  const getCooldownProgress = useCallback(
    (actionType: PetAction['type']) => {
      const end = cooldowns[actionType]
      if (!end) return 0
      const action = PET_ACTIONS.find(a => a.type === actionType)
      if (!action || action.cooldown === 0) return 0
      const remaining = end - Date.now()
      if (remaining <= 0) return 0
      return Math.round((remaining / (action.cooldown * 1000)) * 100)
    },
    [cooldowns]
  )

  const showMessage = useCallback((msg: string) => {
    setLastActionMessage(msg)
    setTimeout(() => setLastActionMessage(null), 3000)
  }, [])

  const executeAction = useCallback(
    (actionType: PetAction['type']) => {
      if (!pet) return
      if (isOnCooldown(actionType)) return


      const action = PET_ACTIONS.find(a => a.type === actionType)
      if (!action) return

      // Пока питомец спит — все действия заблокированы
      if (pet.isSleeping) {
        showMessage('Питомец спит до 8:00')
        return
      }

      const upData: PetStatsDelta = {
        pet_hunger:      action.statChanges.hunger,
        pet_energy:      action.statChanges.energy,
        pet_happiness:   action.statChanges.happiness,
        pet_health:      action.statChanges.health,
        pet_cleanliness: action.statChanges.cleanliness,
        pet_xp:          action.xpGain,
      }

      // Отправляем изменение статов на сервер
      applyStatChanges(upData)

      const messages: Record<PetAction['type'], string[]> = {
        feed:  ['Ням-ням! Вкусно!', 'Спасибо за еду!', 'Объелся...'],
        play:  ['Ура! Играем!',     'Это весело!',      'Ещё раз!'],
        heal:  ['Горькое, но помогает...', 'Уже лучше!'],
        clean: ['Чистый и свежий!', 'Как хорошо пахнет!'],
      }
      const msgList = messages[actionType]
      if (msgList.length > 0) {
        const msg = msgList[Math.floor(Math.random() * msgList.length)]
        showMessage(msg)
        updatePhrase(msg)
      }

      // Кулдаун
      if (action.cooldown > 0) {
        const endTime = Date.now() + action.cooldown * 1000
        setCooldowns(prev => {
          const next = { ...prev, [actionType]: endTime }
          saveCooldowns(next)
          return next
        })
      }
    },
    [pet, isOnCooldown, applyStatChanges, updatePhrase, showMessage]
  )

  return { executeAction, isOnCooldown, getCooldownRemaining, getCooldownProgress, lastActionMessage }
}