import { Link, useLocation} from 'react-router'
import { cn } from '@shared/lib/utils'

const NAV_ITEMS = [
  { href: '/pet', label: 'Питомец', emoji: '' },
  { href: '/leaderboard', label: 'Рейтинг', emoji: '' },
  { href: '/profile', label: "Профиль", emoji: '' }
]

export const Header = () => {
  const location = useLocation()

  return (
    <header className="sticky top-0 z-50 w-full h-15 bg-pet-bg border-b border-white/10">
      <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group">
          <span className="font-display text-xl text-white tracking-wide">
            Digital<span className="text-pet-glow">Pet</span>
          </span>
        </Link>

        {/* Nav + User */}
        <div className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-body font-semibold transition-all duration-200',
                location.pathname === item.href
                  ? 'bg-pet-glow/20 text-pet-glow'
                  : 'text-white/60 hover:text-white hover:bg-white/10'
              )}
            >
              <span>{item.emoji}</span>
              <span className="hidden sm:inline">{item.label}</span>
            </Link>
          ))}
        </div>

      </div>
    </header>
  )
}

