import {useRef, useState} from 'react'
import { useNavigate } from 'react-router'
import { usePetStore, PetAvatar } from '@entities/pet'
import {
  type PetType,
  type PetPersonality,
  type PetFeature,
  PET_FEATURES
} from '@shared/types'
import { PET_TYPES, PET_PERSONALITIES } from '@shared/config/constants'
import { cn } from '@shared/lib/utils'
import { COLORS } from "@shared/config/constants";


export const CreatePetPage = () => {
  const navigate = useNavigate()
  const { createPet } = usePetStore()
  const colorInputRef = useRef<HTMLInputElement>(null)

  const [name, setName] = useState('')
  const [type, setType] = useState<PetType>('cat')
  const [personality, setPersonality] = useState<PetPersonality>('playful')
  const [color, setColor] = useState(COLORS[0])
  const [step, setStep] = useState(1)
  const [customColorActive, setCustomColorActive] = useState(false)

  function getRandomFeature(): PetFeature {
    const index = Math.floor(Math.random() * PET_FEATURES.length)
    return PET_FEATURES[index]
  }
  const handleCreate = () => {
    if (!name.trim()) return
    createPet({
      pet_name: name.trim(),
      pet_species: type,
      pet_color: color,
      pet_character: personality,
      pet_feature: getRandomFeature()
    })

    navigate('/pet')
  }

  const handleCustomColor = (e: React.ChangeEvent<HTMLInputElement>) => {
    setColor(e.target.value)
    setCustomColorActive(true)
  }

  return (
    <div className="h-full bg-pet-bg flex flex-col items-center justify-center px-4 py-8">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-20 w-60 h-60 bg-pet-glow/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 -right-20 w-60 h-60 bg-pet-teal/10 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md space-y-6 animate-fadeIn">
        <div className="text-center">
          <h1 className="font-display text-4xl text-white mb-2">
            Новый<span className="text-pet-glow"> питомец</span>
          </h1>
          <p className="font-body text-white/50 text-sm">Шаг {step} из 4</p>
          {/* Progress */}
          <div className="flex gap-2 justify-center mt-3">
            {[1, 2, 3, 4].map((s) => (
              <div
                key={s}
                className={cn(
                  'h-1.5 rounded-full transition-all duration-300',
                  s === step ? 'w-8 bg-pet-glow' : s < step ? 'w-4 bg-pet-glow/50' : 'w-4 bg-white/20'
                )}
              />
            ))}
          </div>
        </div>

        {/* ── Шаг 1: Вид ─────────────────────────────────────────────── */}
        {step === 1 && (
          <div className="space-y-4 animate-pop">
            <h2 className="font-body font-bold text-white text-center text-lg">Выбери вид питомца</h2>
            <div className="grid grid-cols-2 gap-3">
              {(Object.entries(PET_TYPES) as [PetType, typeof PET_TYPES[PetType]][]).map(([petType, info]) => (
                <button
                  key={petType}
                  onClick={() => setType(petType)}
                  className={cn(
                    'group flex flex-col items-center p-4 rounded-2xl border-2 transition-all duration-200 font-body',
                    type === petType
                      ? 'border-pet-glow bg-pet-glow/20 text-white'
                      : 'border-white/10 bg-white/5 text-white/70 hover:border-white/30 hover:bg-white/10'
                  )}
                >
                  <PetAvatar type={petType} mood="play" color={color} size="md" className={cn("group-hover:-translate-y-1")} />
                  <span className="font-bold mt-2">{info.label}</span>
                </button>
              ))}
            </div>
            <button
              onClick={() => setStep(2)}
              className="w-full py-3 bg-pet-glow hover:bg-pet-glow/80 text-white font-bold font-body rounded-2xl transition-all duration-200 active:scale-95"
            >
              Далее →
            </button>
          </div>
        )}

        {/* ── Шаг 2: Характер ────────────────────────────────────────── */}
        {step === 2 && (
          <div className="space-y-5 animate-pop">
            <h2 className="font-body font-bold text-white text-center text-lg">Характер и цвет</h2>

            <div className="space-y-2">
              <p className="text-white/60 text-sm font-body">Характер:</p>
              <div className="space-y-2">
                {(Object.entries(PET_PERSONALITIES) as [PetPersonality, typeof PET_PERSONALITIES[PetPersonality]][]).map(([pers, info]) => (
                  <button
                    key={pers}
                    onClick={() => setPersonality(pers)}
                    className={cn(
                      'w-full flex items-center gap-3 p-3 rounded-xl border transition-all duration-200 font-body text-left',
                      personality === pers
                        ? 'border-pet-glow bg-pet-glow/15 text-white'
                        : 'border-white/10 bg-white/5 text-white/70 hover:border-white/30'
                    )}
                  >
                    <span className="text-xl">{info.emoji}</span>
                    <div>
                      <p className="font-bold text-sm">{info.label}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setStep(1)}
                className="flex-1 py-3 bg-white/10 hover:bg-white/20 text-white font-bold font-body rounded-2xl transition-all duration-200"
              >
                ← Назад
              </button>
              <button
                onClick={() => setStep(3)}
                className="flex-1 py-3 bg-pet-glow hover:bg-pet-glow/80 text-white font-bold font-body rounded-2xl transition-all duration-200 active:scale-95"
              >
                Далее →
              </button>
            </div>
          </div>
        )}

        {/* ── Шаг 3: Цвет ────────────────────────────────────────────── */}
        {step === 3 && (
          <>
            <div className="space-y-2">
              <p className="text-white/60 text-sm font-body">Цвет питомца:</p>
              <div className="flex gap-2 flex-wrap">
                {COLORS.map((c) => (
                  <button
                    key={c}
                    onClick={() => setColor(c)}
                    className={cn(
                      'w-9 h-9 rounded-full transition-all duration-200 border-2',
                      color === c ? 'scale-125 border-white' : 'border-transparent hover:scale-110'
                    )}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>

            {/* Разделитель */}
            <div className="flex items-center gap-3">
              <div className="flex-1 h-px bg-white/8" />
              <span className="text-white/25 text-xs font-body">или свой цвет</span>
              <div className="flex-1 h-px bg-white/8" />
            </div>

            {/* Кастомный color picker */}
            <div>
              <p className="font-body text-xs font-bold text-white/40 uppercase tracking-wider mb-3">
                Свой цвет
              </p>
              <div className="flex items-center gap-3">
                {/* Большая кнопка-цвет */}
                <button
                  onClick={() => colorInputRef.current?.click()}
                  className={cn(
                    'relative w-14 h-14 rounded-2xl border-2 transition-all duration-200 shrink-0 overflow-hidden',
                    customColorActive
                      ? 'border-white scale-105 shadow-lg'
                      : 'border-white/20 hover:border-white/40 hover:scale-105'
                  )}
                  style={{ backgroundColor: customColorActive ? color : undefined }}
                  title="Выбрать цвет"
                >
                  {!customColorActive && (
                    <div className="absolute inset-0 bg-linear-to-br from-red-400 via-green-400 to-blue-500 opacity-80" />
                  )}
                  <span className="relative z-10 text-xl">
                        {customColorActive ? '' : '🎨'}
                      </span>
                  {/* Скрытый input */}
                  <input
                    ref={colorInputRef}
                    type="color"
                    value={color}
                    onChange={handleCustomColor}
                    className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                  />
                </button>

                <div className="flex-1 space-y-1.5">
                  {/* HEX инпут */}
                  <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 focus-within:border-white/30 transition-colors">
                    <span className="text-white/30 text-sm font-mono">#</span>
                    <input
                      type="text"
                      value={color.replace('#', '')}
                      onChange={(e) => {
                        const val = e.target.value.replace(/[^0-9a-fA-F]/g, '').slice(0, 6)
                        if (val.length === 6) {
                          setColor(`#${val}`)
                          setCustomColorActive(true)
                        }
                      }}
                      placeholder="ff9f43"
                      maxLength={6}
                      className="flex-1 bg-transparent text-white font-mono text-sm placeholder-white/20 focus:outline-none uppercase"
                    />
                  </div>
                  <p className="text-xs font-body text-white/30 px-1">
                    Вставьте hex-код или нажми на палитру
                  </p>
                </div>
              </div>
            </div>

            {/* Preview */}
            <div className="flex justify-center">
              <PetAvatar type={type} mood="neutral" color={color} size="lg" className="animate-float" />
            </div>

            <div className="flex gap-3">
              <button
               onClick={() => setStep(2)}
               className="flex-1 py-3 bg-white/10 hover:bg-white/20 text-white font-bold font-body rounded-2xl transition-all duration-200"
              >
                ← Назад
              </button>
              <button
                onClick={() => setStep(4)}
                className="flex-1 py-3 bg-pet-glow hover:bg-pet-glow/80 text-white font-bold font-body rounded-2xl transition-all duration-200 active:scale-95"
              >
                Далее →
              </button>
            </div>
          </>
        )}

        {/* ── Шаг 4: Имя ─────────────────────────────────────────────── */}
        {step === 4 && (
          <div className="space-y-5 animate-pop">
            <h2 className="font-body font-bold text-white text-center text-lg">Дай имя питомцу!</h2>

            <div className="flex justify-center">
              <PetAvatar type={type} mood="play" color={color} size="xl" className="animate-float" />
            </div>

            <div>
              <input
                autoFocus
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && name.trim() && handleCreate()}
                placeholder="Имя питомца..."
                maxLength={20}
                className="w-full bg-white/10 border border-white/20 rounded-2xl px-4 py-3.5 text-white text-lg font-body text-center placeholder-white/30 focus:outline-none focus:border-pet-glow/60 transition-colors"
              />
              <p className="text-center text-white/30 text-xs mt-2 font-body">{name.length}/20</p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setStep(3)}
                className="flex-1 py-3 bg-white/10 hover:bg-white/20 text-white font-bold font-body rounded-2xl transition-all duration-200"
              >
                ← Назад
              </button>
              <button
                onClick={handleCreate}
                disabled={!name.trim()}
                className="flex-1 py-3 bg-pet-glow hover:bg-pet-glow/80 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold font-body rounded-2xl transition-all duration-200 active:scale-95"
              >
                Создать! 🎉
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
