import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { usePetStore, PetAvatar } from '@entities/pet'
import { StatsPanel } from '@widgets/stats-panel/ui/StatsPanel'
import { ActionBar } from '@widgets/action-bar/ui/ActionBar'
import { ChatWidget } from '@widgets/pet-card/ui/ChatWidget'
import { formatAge, cn } from '@shared/lib/utils'
import {TICK_INTERVAL_MS} from "@shared/config/constants.ts";
import { useWeatherAPI } from '@features/weather-integration/hooks/useWeatherAPI'
import type {PetStateValue} from "@shared/types";


export const PetPage: React.FC = () => {
  const { weather } = useWeatherAPI()
  const pet = usePetStore(state => state.pet)
  const fetchPet = usePetStore(state => state.fetchPet)
  const updatePhrase = usePetStore(state => state.updatePhrase)
  const deletePet = usePetStore(state => state.deletePet)
  const renamePet = usePetStore(state => state.renamePet)
  const navigate = useNavigate()

  const [activeTab, setActiveTab] = useState<'stats' | 'chat'>('stats')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [phraseTimer, setPhraseTimer] = useState(0)
  const [isEditingName, setIsEditingName] = useState(false)
  const [newName, setNewName] = useState('')


  useEffect(() => {
    if (!pet) navigate('/create', { replace: true })
  }, [pet, navigate])

  // ── Поллинг статов каждые 15 минут ──────────────────────────────────────
  useEffect(() => {
    fetchPet() // первый запрос сразу при входе
    const poll = setInterval(() => {
      fetchPet()
    }, TICK_INTERVAL_MS)
    return () => clearInterval(poll)
  }, [fetchPet])


  // ── Смена фразы каждые 15 секунд ────────────────────────────────────────
  useEffect(() => {
    const interval = setInterval(() => {
      updatePhrase()
      setPhraseTimer(t => t + 1)
    }, 30_000)
    return () => clearInterval(interval)
  }, [updatePhrase])

  if (!pet) return null

  const levelProgress = (pet.currentXP / pet.xpToNextLevel) * 100

  const getMoodLabel = (mood: PetStateValue) => {
    switch (mood) {
      case 'neutral':
        return "Нормально";
      case 'sleep':
        return "Спит";
      case 'sad':
        return "Грустный";
      case 'sick1':
        return "Простыл";
      case 'sick2':
        return "Нездоровится";
      case 'sick3':
        return "Болеет";
      default:
        return "Счастлив";
    }
  };

  const handleDelete = () => {
    deletePet()
    navigate('/create')
  }

  const handleRename = async () => {
    if (!newName.trim()) return
    await renamePet(newName.trim())
    setIsEditingName(false)
    setNewName('')
  }

  // ── Карточка питомца ─────────────────────────────────────────────────────
  const PetCard = (
    <div className="bg-white/5 border border-white/10 rounded-3xl p-5 flex flex-col items-center gap-3">

      {/* Имя + статус */}
      <div className="w-full flex items-center justify-between">
        <div>
          <div className="flex flex-col gap-2 w-full">

            {!isEditingName ? (
              <div className="flex gap-x-2 items-center">
                <h1 className="font-display text-xl text-white leading-tight">
                  {pet.name}
                </h1>

                <button
                  onClick={() => {
                    setIsEditingName(true)
                    setNewName(pet.name)
                  }}
                  className="flex w-6 h-6 rounded-full bg-white items-center justify-center cursor-pointer hover:scale-105 transition"
                >
                  <svg width="15" height="15" viewBox="0 0 36 36" fill="none">
                    <path d="M0 28.495V35.995H7.5L29.63 13.865L22.13 6.365L0 28.495ZM35.41 8.085C36.19 7.305 36.19 6.035 35.41 5.255L30.74 0.585C29.96 -0.195 28.69 -0.195 27.91 0.585L24.25 4.245L31.75 11.745L35.41 8.085Z" fill="black"/>
                  </svg>
                </button>
              </div>
            ) : (
              <div className="flex flex-col gap-2 animate-fadeIn">
                <input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="bg-white/10 border border-white/20 rounded-xl px-3 py-1.5 text-sm text-white outline-none focus:border-pet-teal transition"
                  placeholder="Новое имя"
                  maxLength={20}
                />

                <div className="flex gap-2">
                  <button
                    onClick={() => setIsEditingName(false)}
                    className="flex-1 py-1.5 bg-white/10 hover:bg-white/15 text-white rounded-lg text-xs font-bold transition"
                  >
                    Отмена
                  </button>

                  <button
                    onClick={handleRename}
                    disabled={!newName.trim()}
                    className="flex-1 py-1.5 bg-pet-teal hover:opacity-90 disabled:opacity-40 text-white rounded-lg text-xs font-bold transition"
                  >
                    Сохранить
                  </button>
                </div>
              </div>
            )}

            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-xs font-body text-white/40">Ур. {pet.level}</span>
              <span className="text-white/20 text-xs">·</span>
              <span className="text-xs font-body text-white/40">{formatAge(pet.age)}</span>
            </div>
          </div>
        </div>
        <span className="text-xs font-body px-2 py-1 rounded-full bg-white/10 text-white/60 whitespace-nowrap">
          {
            getMoodLabel(pet.mood)
          }
        </span>
      </div>

      {/* XP */}
      <div className="w-full">
        <div className="flex justify-between text-xs font-body text-white/30 mb-1">
          <span>XP</span>
          <span>{pet.currentXP} / {pet.xpToNextLevel}</span>
        </div>
        <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full bg-linear-to-r from-pet-glow to-pet-teal rounded-full transition-all duration-700"
            style={{ width: `${levelProgress}%` }}
          />
        </div>
      </div>

      {/* Аватар */}
      <div className="h-75 relative flex flex-col items-center justify-end py-2 w-full">
        {weather && (
          <div className="absolute top-0 right-0 flex items-center gap-1.5 bg-white/5 border border-white/10 rounded-xl px-2 py-1">
            <span className="text-xs font-mono text-white/50">{weather.temp}°</span>
            <span className="text-xs text-white/30">{weather.description}</span>
          </div>
        )}

        <PetAvatar
          type={pet.type}
          mood={pet.mood}
          color={pet.customColor ?? '#ff9f43'}
          size="xl"
          isSleeping={pet.isSleeping}
        />
      </div>

      {/* Фраза */}
      {pet.currentPhrase && !pet.isSleeping && (
        <div
          key={phraseTimer}
          className="w-full text-center bg-white/8 border border-white/10 rounded-2xl rounded-tl-sm px-3 py-2 animate-pop"
        >
          <p className="text-xs font-body text-white/80">{pet.currentPhrase}</p>
        </div>
      )}
      {pet.isSleeping && (
        <p className="text-xs font-body text-white/40 animate-pulse-slow">Питомец спит...</p>
      )}
    </div>
  )

  // ── Правая панель ────────────────────────────────────────────────────────
  const RightPanel = (
    <div className="flex flex-col gap-4">
      {/* Табы */}
      <div className="flex rounded-xl bg-white/5 p-1 border border-white/10">
        {(['stats', 'chat'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              'flex-1 py-2 text-xs font-bold font-body rounded-lg transition-all duration-200',
              activeTab === tab ? 'bg-white/15 text-white' : 'text-white/40 hover:text-white/60'
            )}
          >
            {tab === 'stats' ? 'Характеристики' : 'Чат'}
          </button>
        ))}
      </div>

      {/* Контент */}
      <div key={activeTab} className="animate-fadeIn">
        {activeTab === 'stats' && (
          <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
            <StatsPanel stats={pet.stats} />
          </div>
        )}
        {activeTab === 'chat' && <ChatWidget />}
      </div>

      {/* Действия */}
      <div className="bg-white/5 border border-white/10 rounded-2xl p-4">
        <h3 className="font-body font-bold text-white/50 text-xs uppercase tracking-wider mb-3">
          Действия
        </h3>
        <ActionBar isSleeping={pet.isSleeping} />
      </div>
    </div>
  )

  // ── Кнопка удаления ──────────────────────────────────────────────────────
  const DeleteButton = (
    <div className="flex justify-center">
      {showDeleteConfirm ? (
        <div className="w-full bg-red-500/10 border border-red-500/30 rounded-2xl p-4 space-y-3 animate-pop">
          <p className="font-body text-white text-sm text-center">
            Питомец <strong>{pet.name}</strong> исчезнет навсегда
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setShowDeleteConfirm(false)}
              className="flex-1 py-2 bg-white/10 hover:bg-white/15 text-white rounded-xl font-body text-sm font-bold transition-all"
            >
              Отмена
            </button>
            <button
              onClick={handleDelete}
              className="flex-1 py-2 bg-red-500/70 hover:bg-red-500/90 text-white rounded-xl font-body text-sm font-bold transition-all"
            >
              Удалить
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowDeleteConfirm(true)}
          className="text-white/20 hover:text-red-400/60 text-xs font-body transition-colors py-1"
        >
          Отпустить питомца
        </button>
      )}
    </div>
  )

  return (
    <div className="min-h-[calc(100vh-60px)] bg-pet-bg px-4 py-6">
      <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-pet-glow/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-pet-teal/5 rounded-full blur-3xl" />
      </div>

      {/* Мобильный */}
      <div className="flex flex-col gap-4 animate-fadeIn lg:hidden max-w-md mx-auto">
        {PetCard}
        {RightPanel}
        {DeleteButton}
      </div>

      {/* Десктоп */}
      <div className="hidden items-start justify-center lg:flex gap-6 animate-fadeIn max-w-5xl mx-auto">
        <div className="shrink-0 w-72 flex flex-col gap-4">
          {PetCard}
          {DeleteButton}
        </div>
        <div className="flex-1 min-w-0">
          {RightPanel}
        </div>
      </div>
    </div>
  )
}