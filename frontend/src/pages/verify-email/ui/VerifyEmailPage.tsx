import React, { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { cn } from '@shared/lib/utils'
import api from '@shared/api/api.ts'

type Status = 'idle' | 'loading' | 'success' | 'error'

export const VerifyEmailPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // Токен может прийти прямо в URL: /verify-email?token=XXX
  const urlToken = searchParams.get('token') ?? ''

  const [token,  setToken]  = useState(urlToken)
  const [status, setStatus] = useState<Status>('idle')
  const [error,  setError]  = useState('')

  // Если токен уже в URL — сразу отправляем
  useEffect(() => {
    if (urlToken) handleVerify(urlToken)
  }, [])

  const handleVerify = async (t = token) => {
    const trimmed = t.trim()
    if (!trimmed) return setError('Введите токен из письма')
    setError('')
    setStatus('loading')
    try {
      await api.get(`/auth/verify-email?token=${encodeURIComponent(trimmed)}`)
      setStatus('success')
    } catch (err: any) {
      setStatus('error')
      setError(err.message ?? 'Неверный или истёкший токен')
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    handleVerify()
  }

  // ── Экран: автоверификация (токен в URL) ─────────────────────────────────
  if (urlToken && status === 'loading') {
    return (
      <Screen>
        <h1 className="font-display text-3xl text-white mb-2">Проверяем...</h1>
        <p className="font-body text-white/50 text-sm">Подтверждаем ваш email</p>
        <div className="mt-6 w-8 h-8 border-2 border-white/20 border-t-pet-teal rounded-full animate-spin mx-auto" />
      </Screen>
    )
  }

  // ── Экран: успех ─────────────────────────────────────────────────────────
  if (status === 'success') {
    return (
      <Screen>
        <div className="text-6xl animate-pop inline-block mb-4">🎉</div>
        <h1 className="font-display text-3xl text-white mb-2">Email подтверждён!</h1>
        <p className="font-body text-white/60 text-sm mb-8">
          Теперь вы можете войти в аккаунт
        </p>
        <button
          onClick={() => navigate('/login')}
          className="w-full py-3.5 rounded-2xl font-body font-bold text-white bg-linear-to-r from-pet-glow to-pet-pink hover:opacity-90 active:scale-95 transition-all shadow-lg shadow-pet-glow/20"
        >
          Войти 🐾
        </button>
      </Screen>
    )
  }

  // ── Экран: ввод токена вручную ────────────────────────────────────────────
  return (
    <Screen>
      {/* Иконка */}
      <h1 className="font-display text-3xl text-white mb-1">Подтверждение email</h1>
      <p className="font-body text-white/50 text-sm mb-8 leading-relaxed">
        Введите токен из письма, которое мы отправили на вашу почту
      </p>

      {/* Ошибка */}
      {status === 'error' && (
        <div className="w-full bg-red-500/15 border border-red-500/30 rounded-xl px-4 py-3 mb-5 animate-pop">
          <p className="text-red-400 text-sm font-body text-center">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="w-full space-y-4">
        {/* Поле токена */}
        <div className="space-y-2">
          <label className="font-body text-xs font-bold text-white/40 uppercase tracking-wider block">
            Токен подтверждения
          </label>
          <input
            type="text"
            value={token}
            onChange={e => { setToken(e.target.value); setError(''); setStatus('idle') }}
            placeholder="Вставьте токен из письма"
            autoComplete="off"
            autoFocus
            className={cn(
              'w-full bg-white/5 border rounded-xl px-4 py-3 text-white font-mono text-sm',
              'placeholder-white/20 focus:outline-none transition-all duration-200',
              error
                ? 'border-red-500/50 focus:border-red-500/80'
                : 'border-white/12 focus:border-pet-teal/50 focus:bg-white/8'
            )}
          />
          {error && <p className="text-red-400 text-xs font-body">{error}</p>}
          <p className="text-white/25 text-xs font-body">
            Токен — это длинная строка символов из письма
          </p>
        </div>

        <button
          type="submit"
          disabled={!token.trim() || status === 'loading'}
          className={cn(
            'w-full py-3.5 rounded-2xl font-body font-bold text-white transition-all duration-200',
            'bg-linear-to-r from-pet-teal to-violet-500 hover:opacity-90 active:scale-95',
            'disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-pet-teal/20'
          )}
        >
          {status === 'loading'
            ? <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Проверяем...
              </span>
            : 'Подтвердить email ✉️'
          }
        </button>
      </form>

      <div className="mt-6 pt-5 border-t border-white/8 w-full text-center">
        <p className="font-body text-white/30 text-xs">
          Письмо не пришло?{' '}
          <span className="text-white/50">Проверьте папку «Спам»</span>
        </p>
        <button
          onClick={() => navigate('/login')}
          className="mt-3 text-white/40 hover:text-white/70 text-xs font-body transition-colors"
        >
          ← Вернуться ко входу
        </button>
      </div>
    </Screen>
  )
}

// Общая обёртка страницы
const Screen: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="min-h-screen bg-pet-bg flex flex-col items-center justify-center px-4 py-8">
    <div className="fixed inset-0 overflow-hidden pointer-events-none">
      <div className="absolute -top-32 -left-32 w-96 h-96 bg-pet-teal/8 rounded-full blur-3xl animate-pulse-slow" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-violet-500/8 rounded-full blur-3xl animate-pulse-slow" />
    </div>
    <div className="relative w-full max-w-sm animate-fadeIn bg-white/5 border border-white/10 rounded-3xl p-8 flex flex-col items-center text-center">
      {children}
    </div>
  </div>
)
