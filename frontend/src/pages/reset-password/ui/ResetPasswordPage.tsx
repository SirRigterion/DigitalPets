import React, { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { cn } from '@shared/lib/utils'
import api from '@shared/api/api.ts'

type Status = 'idle' | 'loading' | 'success' | 'error'

function PasswordStrength({ password }: { password: string }) {
  if (!password) return null
  const score = [
    password.length >= 8,
    /[A-Z]/.test(password) || /[А-Я]/.test(password),
    /[0-9]/.test(password),
    /[^a-zA-Zа-яА-Я0-9]/.test(password),
  ].filter(Boolean).length
  const labels     = ['', 'Слабый',    'Нормальный', 'Хороший',    'Сильный']
  const barColors  = ['', 'bg-red-500', 'bg-yellow-500', 'bg-blue-400', 'bg-green-400']
  const textColors = ['', 'text-red-400', 'text-yellow-400', 'text-blue-300', 'text-green-400']
  return (
    <div className="space-y-1.5">
      <div className="flex gap-1">
        {[1,2,3,4].map(i => (
          <div key={i} className={cn('h-1 flex-1 rounded-full transition-all duration-300', i <= score ? barColors[score] : 'bg-white/10')} />
        ))}
      </div>
      {score > 0 && <p className={cn('text-xs font-body', textColors[score])}>{labels[score]}</p>}
    </div>
  )
}

export const ResetPasswordPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const urlToken = searchParams.get('token') ?? ''

  const [token,           setToken]           = useState(urlToken)
  const [newPassword,     setNewPassword]     = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword,    setShowPassword]    = useState(false)
  const [status,          setStatus]          = useState<Status>('idle')
  const [errors,          setErrors]          = useState<Record<string, string>>({})

  const validate = () => {
    const e: Record<string, string> = {}
    if (!token.trim())                          e.token   = 'Введите токен из письма'
    if (!newPassword)                           e.password = 'Введите новый пароль'
    else if (newPassword.length < 8)            e.password = 'Минимум 8 символов'
    if (!confirmPassword)                       e.confirm  = 'Повторите пароль'
    else if (confirmPassword !== newPassword)   e.confirm  = 'Пароли не совпадают'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    setStatus('loading')
    try {
      await api.post('/users/reset-password/confirm', {
        token:        token.trim(),
        new_password: newPassword,
      })
      setStatus('success')
    } catch (err: any) {
      setStatus('error')
      setErrors({ token: err.message ?? 'Неверный или истёкший токен' })
    }
  }

  // ── Успех ─────────────────────────────────────────────────────────────────
  if (status === 'success') {
    return (
      <Screen>
        <h1 className="font-display text-3xl text-white mb-2">Пароль изменён!</h1>
        <p className="font-body text-white/60 text-sm mb-8">
          Войдите с новым паролем
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

  // ── Форма смены пароля ────────────────────────────────────────────────────
  return (
    <Screen>
      <h1 className="font-display text-3xl text-white mb-1">Новый пароль</h1>
      <p className="font-body text-white/50 text-sm mb-8 leading-relaxed">
        Введите токен из письма и задайте новый пароль
      </p>

      <form onSubmit={handleSubmit} className="w-full space-y-4 text-left">

        {/* Токен */}
        <div className="space-y-1.5">
          <label className="font-body text-xs font-bold text-white/40 uppercase tracking-wider block">
            Токен из письма
          </label>
          <input
            type="text"
            value={token}
            onChange={e => { setToken(e.target.value); setErrors(p => ({ ...p, token: '' })) }}
            placeholder="Вставьте токен"
            autoComplete="off"
            autoFocus={!urlToken}
            className={cn(
              'w-full bg-white/5 border rounded-xl px-4 py-3 text-white font-mono text-sm',
              'placeholder-white/20 focus:outline-none transition-all duration-200',
              errors.token
                ? 'border-red-500/50 focus:border-red-500/80'
                : 'border-white/12 focus:border-pet-glow/50 focus:bg-white/8'
            )}
          />
          {errors.token && <p className="text-red-400 text-xs font-body">{errors.token}</p>}
        </div>

        {/* Разделитель */}
        <div className="flex items-center gap-3 py-1">
          <div className="flex-1 h-px bg-white/8" />
          <span className="text-white/20 text-xs font-body">новый пароль</span>
          <div className="flex-1 h-px bg-white/8" />
        </div>

        {/* Новый пароль */}
        <div className="space-y-1.5">
          <label className="font-body text-xs font-bold text-white/40 uppercase tracking-wider block">
            Новый пароль
          </label>
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              value={newPassword}
              autoFocus={!!urlToken}
              onChange={e => { setNewPassword(e.target.value); setErrors(p => ({ ...p, password: '' })) }}
              placeholder="Минимум 8 символов"
              autoComplete="new-password"
              className={cn(
                'w-full bg-white/5 border rounded-xl px-4 py-3 pr-12 text-white font-body text-sm',
                'placeholder-white/20 focus:outline-none transition-all duration-200',
                errors.password
                  ? 'border-red-500/50 focus:border-red-500/80'
                  : 'border-white/12 focus:border-pet-glow/50 focus:bg-white/8'
              )}
            />
            <button
              type="button"
              onClick={() => setShowPassword(v => !v)}
              tabIndex={-1}
              className="absolute p-1 right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors text-lg cursor-pointer"
            >
              {showPassword ? <svg width="24" height="24" viewBox="0 0 24 24" fill="gray" xmlns="http://www.w3.org/2000/svg">
                <path d="M20.2501 21C20.1516 21.0002 20.054 20.9808 19.963 20.9431C19.872 20.9054 19.7894 20.85 19.7199 20.7802L3.21994 4.28016C3.08522 4.13836 3.01123 3.94955 3.01373 3.75398C3.01624 3.55841 3.09504 3.37155 3.23334 3.23325C3.37164 3.09495 3.5585 3.01615 3.75407 3.01364C3.94964 3.01114 4.13845 3.08513 4.28025 3.21985L20.7803 19.7198C20.8851 19.8247 20.9564 19.9583 20.9854 20.1038C21.0143 20.2492 20.9994 20.4 20.9427 20.537C20.8859 20.674 20.7899 20.7911 20.6666 20.8735C20.5433 20.9559 20.3984 20.9999 20.2501 21Z" fill="gray"/>
                <path d="M11.6245 14.8055L9.19687 12.3778C9.18296 12.364 9.16508 12.3549 9.14574 12.3518C9.1264 12.3487 9.10656 12.3517 9.08903 12.3605C9.0715 12.3692 9.05714 12.3832 9.04799 12.4005C9.03883 12.4179 9.03532 12.4376 9.03797 12.457C9.13598 13.0868 9.43171 13.6692 9.88242 14.1199C10.3331 14.5706 10.9155 14.8664 11.5453 14.9644C11.5647 14.967 11.5845 14.9635 11.6018 14.9543C11.6191 14.9452 11.6331 14.9308 11.6419 14.9133C11.6506 14.8958 11.6536 14.8759 11.6505 14.8566C11.6474 14.8372 11.6383 14.8194 11.6245 14.8055Z" fill="gray"/>
                <path d="M12.3751 9.19452L14.8065 11.625C14.8204 11.639 14.8383 11.6482 14.8577 11.6515C14.8772 11.6547 14.8971 11.6517 14.9148 11.6429C14.9324 11.6341 14.9468 11.62 14.956 11.6026C14.9652 11.5852 14.9686 11.5653 14.9659 11.5458C14.8681 10.9151 14.5722 10.3319 14.1209 9.8806C13.6696 9.42932 13.0864 9.13337 12.4557 9.03561C12.4362 9.0326 12.4162 9.03583 12.3986 9.04486C12.381 9.05388 12.3667 9.06822 12.3578 9.08585C12.3489 9.10347 12.3457 9.12347 12.3488 9.14298C12.3519 9.1625 12.3611 9.18054 12.3751 9.19452Z" fill="gray"/>
                <path d="M23.0157 12.8137C23.1709 12.5702 23.253 12.2872 23.2521 11.9984C23.2513 11.7096 23.1676 11.4271 23.0111 11.1844C21.7707 9.26625 20.1615 7.63688 18.3578 6.47203C16.3595 5.18203 14.1564 4.5 11.9851 4.5C10.8405 4.50157 9.70363 4.6882 8.61856 5.05266C8.58819 5.06276 8.56091 5.08046 8.53932 5.10409C8.51773 5.12772 8.50255 5.15647 8.49522 5.18763C8.48789 5.21878 8.48865 5.25129 8.49744 5.28207C8.50623 5.31284 8.52276 5.34085 8.54543 5.36344L10.7598 7.57781C10.7828 7.60086 10.8114 7.61752 10.8428 7.62615C10.8742 7.63478 10.9073 7.63508 10.9389 7.62703C11.6895 7.44412 12.4745 7.45752 13.2184 7.66595C13.9623 7.87438 14.64 8.27082 15.1863 8.8171C15.7326 9.36338 16.129 10.0411 16.3375 10.785C16.5459 11.5289 16.5593 12.3139 16.3764 13.0645C16.3684 13.096 16.3688 13.129 16.3774 13.1603C16.386 13.1916 16.4026 13.2202 16.4256 13.2431L19.6107 16.4306C19.6439 16.4638 19.6883 16.4834 19.7351 16.4855C19.782 16.4876 19.8279 16.472 19.8639 16.4419C21.0899 15.3968 22.1524 14.1739 23.0157 12.8137Z" fill="gray"/>
                <path d="M12 16.5C11.3188 16.5 10.6465 16.3454 10.0337 16.0478C9.42094 15.7502 8.88375 15.3173 8.46263 14.7819C8.04151 14.2464 7.74745 13.6224 7.60262 12.9567C7.45779 12.2911 7.46598 11.6012 7.62656 10.9392C7.63452 10.9077 7.63417 10.8747 7.62555 10.8434C7.61692 10.8121 7.60031 10.7836 7.57734 10.7606L4.44422 7.6261C4.41099 7.59284 4.36649 7.57327 4.31952 7.57128C4.27255 7.56928 4.22655 7.585 4.19062 7.61532C3.04734 8.59079 1.9875 9.77766 1.01859 11.1647C0.84899 11.4081 0.755584 11.6965 0.750243 11.9931C0.744901 12.2897 0.827865 12.5813 0.988591 12.8306C2.22656 14.768 3.81937 16.3997 5.59547 17.5486C7.59656 18.8438 9.74625 19.5 11.985 19.5C13.1412 19.4969 14.2899 19.3143 15.39 18.9586C15.4206 18.9488 15.4482 18.9313 15.4702 18.9078C15.4921 18.8842 15.5076 18.8554 15.5152 18.8242C15.5227 18.7929 15.5222 18.7602 15.5134 18.7293C15.5047 18.6983 15.4882 18.6701 15.4655 18.6474L13.2403 16.4227C13.2174 16.3997 13.1888 16.3831 13.1575 16.3745C13.1262 16.3658 13.0932 16.3655 13.0617 16.3734C12.7141 16.4577 12.3577 16.5002 12 16.5Z" fill="gray"/>
              </svg> : <svg width="24" height="24" viewBox="0 0 24 24" fill="gray" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15Z" fill="gray"/>
                  <path d="M23.0081 11.1844C21.7678 9.26625 20.1586 7.63688 18.3548 6.47203C16.3593 5.18203 14.1562 4.5 11.984 4.5C9.9909 4.5 8.03105 5.06953 6.15886 6.19266C4.24965 7.33781 2.51996 9.01078 1.01761 11.1647C0.848014 11.4081 0.754608 11.6965 0.749266 11.9931C0.743924 12.2897 0.826888 12.5813 0.987615 12.8306C2.22558 14.768 3.81886 16.3997 5.59449 17.5486C7.59371 18.8437 9.74527 19.5 11.984 19.5C14.1736 19.5 16.3814 18.8236 18.3684 17.5444C20.1712 16.3833 21.7771 14.7478 23.0128 12.8137C23.168 12.5702 23.25 12.2872 23.2492 11.9984C23.2483 11.7096 23.1647 11.4271 23.0081 11.1844V11.1844ZM12 16.5C11.1099 16.5 10.2399 16.2361 9.49989 15.7416C8.75987 15.2471 8.18309 14.5443 7.8425 13.7221C7.50191 12.8998 7.41279 11.995 7.58642 11.1221C7.76006 10.2492 8.18864 9.44736 8.81798 8.81802C9.44731 8.18868 10.2491 7.7601 11.1221 7.58647C11.995 7.41283 12.8998 7.50195 13.722 7.84254C14.5443 8.18314 15.2471 8.75991 15.7416 9.49993C16.236 10.24 16.5 11.11 16.5 12C16.4986 13.1931 16.024 14.3369 15.1804 15.1805C14.3368 16.0241 13.193 16.4986 12 16.5V16.5Z" fill="gray"/>
                </svg>}
            </button>
          </div>
          {errors.password && <p className="text-red-400 text-xs font-body">{errors.password}</p>}
          <PasswordStrength password={newPassword} />
        </div>

        {/* Подтверждение */}
        <div className="space-y-1.5">
          <label className="font-body text-xs font-bold text-white/40 uppercase tracking-wider block">
            Повторите пароль
          </label>
          <input
            type={showPassword ? 'text' : 'password'}
            value={confirmPassword}
            onChange={e => { setConfirmPassword(e.target.value); setErrors(p => ({ ...p, confirm: '' })) }}
            placeholder="••••••••"
            autoComplete="new-password"
            className={cn(
              'w-full bg-white/5 border rounded-xl px-4 py-3 text-white font-body text-sm',
              'placeholder-white/20 focus:outline-none transition-all duration-200',
              errors.confirm
                ? 'border-red-500/50 focus:border-red-500/80'
                : confirmPassword && confirmPassword === newPassword
                  ? 'border-green-500/40'
                  : 'border-white/12 focus:border-pet-glow/50 focus:bg-white/8'
            )}
          />
          {errors.confirm && <p className="text-red-400 text-xs font-body">{errors.confirm}</p>}
          {!errors.confirm && confirmPassword && confirmPassword === newPassword && (
            <p className="text-green-400 text-xs font-body">✓ Пароли совпадают</p>
          )}
        </div>

        <button
          type="submit"
          disabled={status === 'loading'}
          className={cn(
            'w-full py-3.5 rounded-2xl font-body font-bold text-white transition-all duration-200 mt-2',
            'bg-linear-to-r from-pet-glow to-pet-pink hover:opacity-90 active:scale-95',
            'disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-pet-glow/20'
          )}
        >
          {status === 'loading'
            ? <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Сохраняем...
              </span>
            : 'Сохранить пароль'
          }
        </button>
      </form>

      <div className="mt-5 pt-5 border-t border-white/8 w-full text-center">
        <button
          onClick={() => navigate('/login')}
          className="text-white/40 hover:text-white/70 text-xs font-body transition-colors"
        >
          ← Вернуться ко входу
        </button>
      </div>
    </Screen>
  )
}

const Screen: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="min-h-screen bg-pet-bg flex flex-col items-center justify-center px-4 py-8">
    <div className="fixed inset-0 overflow-hidden pointer-events-none">
      <div className="absolute -top-32 -right-32 w-96 h-96 bg-pet-glow/8 rounded-full blur-3xl animate-pulse-slow" />
      <div className="absolute -bottom-32 -left-32 w-96 h-96 bg-pet-teal/8 rounded-full blur-3xl animate-pulse-slow" />
    </div>
    <div className="relative w-full max-w-sm animate-fadeIn bg-white/5 border border-white/10 rounded-3xl p-8 flex flex-col items-center text-center">
      {children}
    </div>
  </div>
)
