import { usePetStore, PetAvatar } from '@entities/pet'
import { PET_TYPES } from '@shared/config/constants'

const MOCK_LEADERBOARD = [
  { name: 'Пушок', type: 'cat' as const, level: 15, color: '#ff9f43'},
  { name: 'Барбос', type: 'dog' as const, level: 12, color: '#48dbfb'},
  { name: 'Флаффи', type: 'rabbit' as const, level: 10, color: '#ff6b9d'},
  { name: 'Игнис', type: 'dragon' as const, level: 8, color: '#a29bfe'},
  { name: 'Рыжик', type: 'fox' as const, level: 7, color: '#fd7f6f'},
]

export const LeaderboardPage = () => {
  const { pet } = usePetStore()

  const MEDALS = ['🥇', '🥈', '🥉']

  return (
    <div className="min-h-screen bg-pet-bg pb-8">
      <div className="max-w-md mx-auto px-4 pt-6 space-y-5 animate-fadeIn">
        <div className="text-center">
          <h1 className="font-display text-3xl text-white">
            <span className="text-pet-glow">Рейтинг</span>
          </h1>
          <p className="font-body text-white/40 text-sm mt-1">Лучшие питомцы</p>
        </div>

        {/* My pet card */}
        {pet && (
          <div className="bg-pet-glow/10 border border-pet-glow/30 rounded-2xl p-4 flex items-center gap-4">
            <PetAvatar type={pet.type} mood={pet.mood} color={pet.customColor ?? '#ff9f43'} size="sm" />
            <div className="flex-1 min-w-0">
              <p className="font-display text-white text-lg">{pet.name}</p>
              <p className="font-body text-white/50 text-sm">
                {PET_TYPES[pet.type].label} · Ур. {pet.level}
              </p>
            </div>
          </div>
        )}

        {/* Leaderboard */}
        <div className="space-y-3">
          {MOCK_LEADERBOARD.map((entry, idx) => (
            <div
              key={entry.name}
              className="flex items-center gap-4 bg-white/5 border border-white/10 rounded-2xl p-4 hover:bg-white/8 transition-colors"
              style={{ animationDelay: `${idx * 80}ms` }}
            >
              <span className="text-white text-2xl w-8 text-center">
                {idx < 3 ? MEDALS[idx] : `#${idx + 1}`}
              </span>
              <PetAvatar type={entry.type} mood="happy" color={entry.color} size="sm" />
              <div className="flex-1 min-w-0">
                <p className="font-body font-bold text-white">{entry.name}</p>
              </div>
              <div className="text-right">
                <p className="font-mono text-pet-lime font-bold">Ур. {entry.level}</p>
              </div>
            </div>
          ))}
        </div>

        <p className="text-center font-body text-white/20 text-xs">
          Играй с питомцем, чтобы попасть в рейтинг! 🐾
        </p>
      </div>
    </div>
  )
}
