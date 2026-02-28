/*
import React, { useState, useRef } from 'react'
import { useNavigate } from 'react-router'
import { useAuthStore } from '@entities/auth'
import { usePetStore } from '@entities/pet'
import { cn } from '@shared/lib/utils'

function getInitials(login: string): string {
  return login.slice(0, 2).toUpperCase()
}

const AVATAR_GRADIENTS = [
  'from-pet-glow to-pet-pink',
  'from-pet-teal to-blue-500',
  'from-violet-500 to-pet-glow',
  'from-amber-400 to-orange-500',
  'from-green-400 to-pet-teal',
]
function getAvatarGradient(login: string): string {
  return AVATAR_GRADIENTS[login.charCodeAt(0) % AVATAR_GRADIENTS.length]
}

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
    <div className="px-5 py-3.5 border-b border-white/8 flex items-center gap-2">
      <h2 className="font-body font-bold text-white/70 text-sm uppercase tracking-wider">{title}</h2>
    </div>
    <div className="p-5">{children}</div>
  </div>
)

const Field: React.FC<{
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
  placeholder?: string
  error?: string
  hint?: string
  autoFocus?: boolean
}> = ({ label, value, onChange, type = 'text', placeholder, error, hint, autoFocus }) => (
  <div className="space-y-1.5">
    <label className="font-body text-xs font-bold text-white/40 uppercase tracking-wider block">
      {label}
    </label>
    <input
      type={type}
      value={value}
      autoFocus={autoFocus}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      autoComplete="off"
      className={cn(
        'w-full bg-white/5 border rounded-xl px-4 py-2.5 text-white font-body text-sm',
        'placeholder-white/20 focus:outline-none transition-all duration-200',
        error
          ? 'border-red-500/50 focus:border-red-500/80'
          : 'border-white/12 focus:border-white/30 focus:bg-white/8'
      )}
    />
    {error && <p className="text-red-400 text-xs font-body">{error}</p>}
    {hint && !error && <p className="text-white/25 text-xs font-body">{hint}</p>}
  </div>
)

export const ProfilePage: React.FC = () => {
  const navigate = useNavigate()
  const {
    user, isLoading,
    updateUsername,
    updateEmail,
    uploadAvatar,
    requestPasswordReset,
    deleteAccount,
  } = useAuthStore()
  const { pet } = usePetStore()

  // ── Аватарка ──────────────────────────────────────────────────────────────
  const avatarInputRef = useRef<HTMLInputElement>(null)
  const [avatarLoading, setAvatarLoading] = useState(false)

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) return
    if (file.size > 2 * 1024 * 1024) return
    setAvatarLoading(true)
    try { await uploadAvatar(file) } catch {}
    setAvatarLoading(false)
    e.target.value = ''
  }

  const avatarSrc = user?.user_avatar
    ? `/api/v1/images/private/${user.user_avatar}`
    : null

  // ── Имя пользователя ──────────────────────────────────────────────────────
  const [usernameVal,   setUsernameVal]   = useState(user?.user_login ?? '')
  const [usernameError, setUsernameError] = useState('')
  const [usernameSaved, setUsernameSaved] = useState(false)

  const handleSaveUsername = async () => {
    const val = usernameVal.trim()
    if (val === user?.user_login) return
    if (val.length < 3) return setUsernameError('Минимум 3 символа')
    if (!/^[a-zA-Z0-9_а-яА-Я]+$/.test(val)) return setUsernameError('Только буквы, цифры и _')
    setUsernameError('')
    try {
      await updateUsername(val)
      setUsernameSaved(true)
      setTimeout(() => setUsernameSaved(false), 2500)
    } catch (e: any) { setUsernameError(e.message) }
  }

  // ── Email ─────────────────────────────────────────────────────────────────
  const [showEmailForm, setShowEmailForm] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [emailError, setEmailError] = useState('')
  const [emailSent, setEmailSent] = useState(false)

  const handleSendEmailChange = async () => {
    if (!newEmail.trim())                                 return setEmailError('Введите новый email')
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newEmail))    return setEmailError('Некорректный email')
    if (newEmail.trim() === user?.user_email)              return setEmailError('Это уже ваш текущий email')
    setEmailError('')
    try {
      await updateEmail(newEmail.trim())
      setEmailSent(true)
    } catch (e: any) { setEmailError(e.message) }
  }

  const resetEmailForm = () => {
    setShowEmailForm(false); setNewEmail(''); setEmailError(''); setEmailSent(false)
  }

  // ── Пароль ────────────────────────────────────────────────────────────────
  const [passwordResetSent, setPasswordResetSent] = useState(false)
  const [passwordResetErr,  setPasswordResetErr]  = useState('')
  const [passwordResetLoad, setPasswordResetLoad] = useState(false)

  const handlePasswordReset = async () => {
    setPasswordResetErr('')
    setPasswordResetLoad(true)
    try {
      await requestPasswordReset()
      setPasswordResetSent(true)
    } catch (e: any) { setPasswordResetErr(e.message) }
    finally { setPasswordResetLoad(false) }
  }

  // ── Удаление ──────────────────────────────────────────────────────────────
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteError,       setDeleteError]       = useState('')

  const handleDelete = async () => {
    setDeleteError('')
    try {
      await deleteAccount()
      navigate('/login', { replace: true })
    } catch (e: any) { setDeleteError(e.message) }
  }

  if (!user) return null

  return (
    <div className="min-h-[calc(100vh-56px)] bg-pet-bg flex items-start justify-center px-4 py-8">

      <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
        <div className="absolute top-20 right-1/4 w-72 h-72 bg-pet-glow/5 rounded-full blur-3xl" />
        <div className="absolute bottom-20 left-1/4 w-60 h-60 bg-pet-teal/5 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-2xl space-y-5 animate-fadeIn">

        {/!* ── Шапка профиля ────────────────────────────────────────────── *!/}
        <div className="bg-white/5 border border-white/10 rounded-3xl p-6">
          <input
            ref={avatarInputRef}
            type="file"
            accept="image/!*"
            onChange={handleAvatarChange}
            className="hidden"
          />

          {/!* Верхняя строка: аватарка + инфо *!/}
          <div className="flex items-start gap-5">

            {/!* Аватарка *!/}
            <div className="shrink-0">
              {avatarLoading ? (
                <div className="w-20 h-20 rounded-2xl bg-white/10 flex items-center justify-center">
                  <span className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                </div>
              ) : avatarSrc ? (
                <img src={avatarSrc} alt="avatar" className="w-20 h-20 rounded-2xl object-cover" />
              ) : (
                <div className={cn(
                  'w-20 h-20 rounded-2xl flex items-center justify-center text-2xl font-bold text-white',
                  'bg-linear-to-br shadow-lg',
                  getAvatarGradient(user.user_login)
                )}>
                  {getInitials(user.user_login)}
                </div>
              )}
            </div>

            {/!* Инфо *!/}
            <div className="min-w-0 flex-1">
              <h1 className="font-display text-2xl text-white truncate">{user.user_login}</h1>
              {user.user_full_name && user.user_full_name !== user.user_login && (
                <p className="font-body text-sm text-white/50 mt-0.5 truncate">{user.user_full_name}</p>
              )}
              <p className="font-body text-sm text-white/40 mt-0.5 truncate">{user.user_email}</p>
              {pet && (
                <p className="text-xs font-body text-white/25 mt-1.5">
                  Питомец: {pet.name} · Ур. {pet.level}
                </p>
              )}
            </div>

          </div>

          {/!* Нижняя строка: кнопки аватарки — прижаты к правому нижнему углу *!/}
          <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-white/6">
            {avatarSrc && (
              <button
                onClick={() => uploadAvatar(new File([], ''))}
                disabled={avatarLoading}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-body text-xs font-semibold transition-all',
                  'bg-red-500/10 hover:bg-red-500/20 text-red-400/70 hover:text-red-400',
                  'border border-red-500/15 hover:border-red-500/30',
                  'disabled:opacity-40 disabled:cursor-not-allowed'
                )}
              >
                {/!* иконка мусорки *!/}
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                  <path d="M10 11v6M14 11v6"/>
                  <path d="M9 6V4h6v2"/>
                </svg>
                Удалить фото
              </button>
            )}
            <button
              onClick={() => avatarInputRef.current?.click()}
              disabled={avatarLoading}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-body text-xs font-semibold transition-all',
                'bg-white/6 hover:bg-white/12 text-white/50 hover:text-white/80',
                'border border-white/8 hover:border-white/18',
                'disabled:opacity-40 disabled:cursor-not-allowed'
              )}
            >
              {/!* иконка загрузки *!/}
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              {avatarSrc ? 'Изменить фото' : 'Загрузить фото'}
            </button>
          </div>
        </div>

        {/!* ── Имя пользователя ─────────────────────────────────────────── *!/}
        <Section title="Имя пользователя">
          <div className="flex gap-3 items-center">
            <div className="flex-1">
              <Field
                label="Новый логин"
                value={usernameVal}
                onChange={v => { setUsernameVal(v); setUsernameError('') }}
                placeholder={user.user_login}
                error={usernameError}
                hint="Только буквы, цифры и _ · минимум 3 символа"
              />
            </div>
            <button
              onClick={handleSaveUsername}
              disabled={isLoading || usernameVal.trim() === user.user_login || !usernameVal.trim()}
              className={cn(
                'px-5 py-2.5 rounded-xl font-body font-bold text-sm transition-all shrink-0',
                usernameSaved
                  ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                  : 'bg-pet-glow/20 hover:bg-pet-glow/30 text-pet-glow border border-pet-glow/20',
                'disabled:opacity-30 disabled:cursor-not-allowed'
              )}
            >
              {usernameSaved ? '✓ Сохранено' : isLoading ? '...' : 'Сохранить'}
            </button>
          </div>
        </Section>

        {/!* ── Email ────────────────────────────────────────────────────── *!/}
        <Section title="Email">
          {!showEmailForm ? (
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-body text-white text-sm">{user.user_email}</p>
                <p className="font-body text-white/30 text-xs mt-0.5">
                  Для смены — отправим письмо с подтверждением на новый адрес
                </p>
              </div>
              <button
                onClick={() => setShowEmailForm(true)}
                className="px-4 py-2 shrink-0 bg-white/8 hover:bg-white/15 text-white/70 hover:text-white border border-white/10 rounded-xl font-body text-sm font-bold transition-all"
              >
                Изменить
              </button>
            </div>
          ) : emailSent ? (
            <div className="space-y-4">
              <div className="bg-pet-teal/10 border border-pet-teal/25 rounded-xl px-4 py-4 text-center">
                <p className="text-3xl mb-2">✉️</p>
                <p className="text-white font-body text-sm font-bold">Письмо отправлено!</p>
                <p className="text-white/50 font-body text-xs mt-1 leading-relaxed">
                  Мы отправили письмо на <span className="text-white/80">{newEmail}</span>.
                  Перейдите по ссылке, чтобы подтвердить смену email.
                </p>
              </div>
              <button onClick={resetEmailForm}
                className="w-full py-2.5 bg-white/8 hover:bg-white/15 text-white/60 rounded-xl font-body text-sm font-bold transition-all">
                Закрыть
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <Field
                label="Новый email"
                value={newEmail}
                onChange={v => { setNewEmail(v); setEmailError('') }}
                type="email"
                placeholder="new@example.com"
                error={emailError}
                autoFocus
              />
              <p className="text-white/30 text-xs font-body">
                Текущий email останется активным до подтверждения нового.
              </p>
              <div className="flex gap-2 pt-1">
                <button onClick={resetEmailForm}
                  className="flex-1 py-2.5 bg-white/8 hover:bg-white/15 text-white/60 rounded-xl font-body text-sm font-bold transition-all">
                  Отмена
                </button>
                <button onClick={handleSendEmailChange} disabled={isLoading || !newEmail.trim()}
                  className="flex-1 py-2.5 bg-pet-teal/20 hover:bg-pet-teal/30 text-pet-teal border border-pet-teal/20 rounded-xl font-body text-sm font-bold transition-all disabled:opacity-40">
                  {isLoading ? '...' : 'Отправить письмо'}
                </button>
              </div>
            </div>
          )}
        </Section>

        {/!* ── Пароль ───────────────────────────────────────────────────── *!/}
        <Section title="Пароль">
          {passwordResetSent ? (
            <div className="space-y-4">
              <div className="bg-pet-glow/10 border border-pet-glow/25 rounded-xl px-4 py-4 text-center">
                <p className="text-3xl mb-2">🔐</p>
                <p className="text-white font-body text-sm font-bold">Письмо отправлено!</p>
                <p className="text-white/50 font-body text-xs mt-1 leading-relaxed">
                  Инструкция по сбросу пароля отправлена на{' '}
                  <span className="text-white/80">{user.user_email}</span>.
                </p>
              </div>
              <button onClick={() => setPasswordResetSent(false)}
                className="w-full py-2.5 bg-white/8 hover:bg-white/15 text-white/60 rounded-xl font-body text-sm font-bold transition-all">
                Закрыть
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-body text-white text-sm">••••••••</p>
                <p className="font-body text-white/30 text-xs mt-0.5">
                  Ссылка для сброса придёт на {user.user_email}
                </p>
                {passwordResetErr && (
                  <p className="text-red-400 text-xs font-body mt-1">{passwordResetErr}</p>
                )}
              </div>
              <button
                onClick={handlePasswordReset}
                disabled={passwordResetLoad}
                className="px-4 py-2 shrink-0 bg-white/8 hover:bg-white/15 text-white/70 hover:text-white border border-white/10 rounded-xl font-body text-sm font-bold transition-all disabled:opacity-40"
              >
                {passwordResetLoad ? '...' : 'Сбросить'}
              </button>
            </div>
          )}
        </Section>

        {/!* ── Удаление аккаунта ─────────────────────────────────────────── *!/}
        <Section title="Удалить аккаунт">
          {!showDeleteConfirm ? (
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-body text-white/60 text-sm">Аккаунт будет удален.
                  Вы сможете восстановить их в течение ограниченного времени.</p>
              </div>
              <button onClick={() => setShowDeleteConfirm(true)}
                className="px-4 py-2 shrink-0 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-xl font-body text-sm font-bold transition-all">
                Удалить
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
                <p className="text-red-400 text-sm font-body">
                  Будут удалены: аккаунт <strong>{user.user_login}</strong>
                </p>
              </div>
              {deleteError && <p className="text-red-400 text-xs font-body">{deleteError}</p>}
              <div className="flex gap-2">
                <button onClick={() => { setShowDeleteConfirm(false); setDeleteError('') }}
                  className="flex-1 py-2.5 bg-white/8 hover:bg-white/15 text-white/60 rounded-xl font-body text-sm font-bold transition-all">
                  Отмена
                </button>
                <button onClick={handleDelete} disabled={isLoading}
                  className="flex-1 py-2.5 bg-red-500/70 hover:bg-red-500/90 text-white rounded-xl font-body text-sm font-bold transition-all disabled:opacity-40 disabled:cursor-not-allowed">
                  {isLoading ? '...' : 'Удалить'}
                </button>
              </div>
            </div>
          )}
        </Section>

      </div>
    </div>
  )
}
*/





import React, { useState, useRef } from 'react'
import { useNavigate } from 'react-router'
import { useAuthStore } from '@entities/auth'
import { cn } from '@shared/lib/utils'

function getInitials(login: string): string {
  return login.slice(0, 2).toUpperCase()
}

const AVATAR_GRADIENTS = [
  'from-pet-glow to-pet-pink',
  'from-pet-teal to-blue-500',
  'from-violet-500 to-pet-glow',
  'from-amber-400 to-orange-500',
  'from-green-400 to-pet-teal',
]
function getAvatarGradient(login: string): string {
  return AVATAR_GRADIENTS[login.charCodeAt(0) % AVATAR_GRADIENTS.length]
}

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
    <div className="px-5 py-3.5 border-b border-white/10">
      <h2 className="font-body font-bold text-white/60 text-xs uppercase tracking-widest">{title}</h2>
    </div>
    <div className="p-5">{children}</div>
  </div>
)

const Field: React.FC<{
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
  placeholder?: string
  error?: string
  hint?: string
  autoFocus?: boolean
}> = ({ label, value, onChange, type = 'text', placeholder, error, hint, autoFocus }) => (
  <div className="space-y-1.5">
    <label className="font-body text-xs font-bold text-white/40 uppercase tracking-wider block">
      {label}
    </label>
    <input
      type={type}
      value={value}
      autoFocus={autoFocus}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      autoComplete="off"
      className={cn(
        'w-full bg-white/5 border rounded-xl px-4 py-2.5 text-white font-body text-sm',
        'placeholder-white/20 focus:outline-none transition-all duration-200',
        error
          ? 'border-red-500/50 focus:border-red-500/80'
          : 'border-white/12 focus:border-white/30 focus:bg-white/8'
      )}
    />
    {error && <p className="text-red-400 text-xs font-body">{error}</p>}
    {hint && !error && <p className="text-white/25 text-xs font-body">{hint}</p>}
  </div>
)

export const ProfilePage: React.FC = () => {
  const navigate = useNavigate()
  const {
    user, isLoading,
    updateUsername,
    updateEmail,
    uploadAvatar,
    requestPasswordReset,
    deleteAccount,
    logout,
  } = useAuthStore()

  // ── Аватарка ──────────────────────────────────────────────────────────────
  const avatarInputRef = useRef<HTMLInputElement>(null)
  const [avatarLoading, setAvatarLoading] = useState(false)

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) return
    if (file.size > 2 * 1024 * 1024) return
    setAvatarLoading(true)
    try { await uploadAvatar(file) } catch {}
    setAvatarLoading(false)
    e.target.value = ''
  }

  const avatarSrc = user?.user_avatar
    ? `/api/v1/images/${user.user_avatar}`
    : null

  // ── Имя пользователя ──────────────────────────────────────────────────────
  const [usernameVal,   setUsernameVal]   = useState(user?.user_login ?? '')
  const [usernameError, setUsernameError] = useState('')
  const [usernameSaved, setUsernameSaved] = useState(false)

  const handleSaveUsername = async () => {
    const val = usernameVal.trim()
    if (val === user?.user_login) return
    if (val.length < 3)                              return setUsernameError('Минимум 3 символа')
    if (!/^[a-zA-Z0-9_а-яА-Я]+$/.test(val))         return setUsernameError('Только буквы, цифры и _')
    setUsernameError('')
    try {
      await updateUsername(val)
      setUsernameSaved(true)
      setTimeout(() => setUsernameSaved(false), 2500)
    } catch (e: any) { setUsernameError(e.message) }
  }

  // ── Email ─────────────────────────────────────────────────────────────────
  const [showEmailForm, setShowEmailForm] = useState(false)
  const [newEmail,      setNewEmail]      = useState('')
  const [emailError,    setEmailError]    = useState('')
  const [emailSent,     setEmailSent]     = useState(false)

  const handleSendEmailChange = async () => {
    if (!newEmail.trim())                                return setEmailError('Введите новый email')
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newEmail))   return setEmailError('Некорректный email')
    if (newEmail.trim() === user?.user_email)             return setEmailError('Это уже ваш текущий email')
    setEmailError('')
    try {
      await updateEmail(newEmail.trim())
      setEmailSent(true)
    } catch (e: any) { setEmailError(e.message) }
  }

  const resetEmailForm = () => {
    setShowEmailForm(false); setNewEmail(''); setEmailError(''); setEmailSent(false)
  }

  // ── Пароль ────────────────────────────────────────────────────────────────
  const [passwordResetSent, setPasswordResetSent] = useState(false)
  const [passwordResetErr,  setPasswordResetErr]  = useState('')
  const [passwordResetLoad, setPasswordResetLoad] = useState(false)

  const handlePasswordReset = async () => {
    setPasswordResetErr('')
    setPasswordResetLoad(true)
    try {
      await requestPasswordReset()
      setPasswordResetSent(true)
    } catch (e: any) { setPasswordResetErr(e.message) }
    finally { setPasswordResetLoad(false) }
  }

  // ── Выход ─────────────────────────────────────────────────────────────────
  const [logoutLoading, setLogoutLoading] = useState(false)

  const handleLogout = async () => {
    setLogoutLoading(true)
    try {
      await logout()
      navigate('/login', { replace: true })
    } finally {
      setLogoutLoading(false)
    }
  }

  // ── Удаление ──────────────────────────────────────────────────────────────
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteError,       setDeleteError]       = useState('')

  const handleDelete = async () => {
    setDeleteError('')
    try {
      await deleteAccount()
      navigate('/login', { replace: true })
    } catch (e: any) { setDeleteError(e.message) }
  }

  if (!user) return null

  return (
    <div className="min-h-[calc(100vh-56px)] bg-pet-bg flex items-start justify-center px-4 py-8">

      <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
        <div className="absolute top-20 right-1/4 w-72 h-72 bg-pet-glow/5 rounded-full blur-3xl" />
        <div className="absolute bottom-20 left-1/4 w-60 h-60 bg-pet-teal/5 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-2xl space-y-5 animate-fadeIn">

        {/* ── Шапка ────────────────────────────────────────────────────── */}
        <div className="bg-white/5 border border-white/10 rounded-3xl p-6">
          <input ref={avatarInputRef} type="file" accept="image/*" onChange={handleAvatarChange} className="hidden" />

          <div className="flex items-start gap-5">
            {/* Аватарка */}
            <div className="shrink-0">
              {avatarLoading ? (
                <div className="w-20 h-20 rounded-2xl bg-white/10 flex items-center justify-center">
                  <span className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                </div>
              ) : avatarSrc ? (
                <img src={avatarSrc} alt="avatar" className="w-20 h-20 rounded-2xl object-cover" />
              ) : (
                <div className={cn(
                  'w-20 h-20 rounded-2xl flex items-center justify-center',
                  'text-xl font-bold text-white select-none',
                  'bg-linear-to-br shadow-lg',
                  getAvatarGradient(user.user_login)
                )}>
                  {getInitials(user.user_login)}
                </div>
              )}
            </div>

            {/* Инфо */}
            <div className="min-w-0 flex-1">
              <h1 className="font-display text-2xl text-white truncate">{user.user_login}</h1>
              {user.user_full_name && user.user_full_name !== user.user_login && (
                <p className="font-body text-sm text-white/50 mt-0.5 truncate">{user.user_full_name}</p>
              )}
              <p className="font-body text-sm text-white/40 mt-0.5 truncate">{user.user_email}</p>
            </div>
          </div>

          {/* Кнопки аватарки */}
          <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-white/6">
            {avatarSrc && (
              <button
                onClick={() => uploadAvatar(new File([], ''))}
                disabled={avatarLoading}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-body text-xs font-semibold transition-all',
                  'bg-red-500/10 hover:bg-red-500/20 text-red-400/70 hover:text-red-400',
                  'border border-red-500/15 hover:border-red-500/30 disabled:opacity-40 disabled:cursor-not-allowed'
                )}
              >
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                  <path d="M10 11v6M14 11v6M9 6V4h6v2"/>
                </svg>
                Удалить фото
              </button>
            )}
            <button
              onClick={() => avatarInputRef.current?.click()}
              disabled={avatarLoading}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-body text-xs font-semibold transition-all',
                'bg-white/6 hover:bg-white/12 text-white/50 hover:text-white/80',
                'border border-white/8 hover:border-white/18 disabled:opacity-40 disabled:cursor-not-allowed'
              )}
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              {avatarSrc ? 'Изменить фото' : 'Загрузить фото'}
            </button>
          </div>
        </div>

        {/* ── Имя пользователя ─────────────────────────────────────────── */}
        <Section title="Имя пользователя">
          <div className="flex gap-3 items-center">
            <div className="flex-1">
              <Field
                label="Новый логин"
                value={usernameVal}
                onChange={v => { setUsernameVal(v); setUsernameError('') }}
                placeholder={user.user_login}
                error={usernameError}
                hint="Только буквы, цифры и _ · минимум 3 символа"
              />
            </div>
            <button
              onClick={handleSaveUsername}
              disabled={isLoading || usernameVal.trim() === user.user_login || !usernameVal.trim()}
              className={cn("px-5 py-2.5 rounded-xl font-body font-bold text-sm transition-all shrink-0",
                usernameSaved
                  ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                  : "bg-white/8 hover:bg-white/15 text-white/70 hover:text-white border border-white/10",
                'disabled:opacity-30 disabled:cursor-not-allowed'
              )}
            >
              {usernameSaved ? 'Сохранено' : isLoading ? '...' : 'Сохранить'}
            </button>
          </div>
        </Section>

        {/* ── Email ────────────────────────────────────────────────────── */}
        <Section title="Email">
          {!showEmailForm ? (
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-body text-white text-sm">{user.user_email}</p>
                <p className="font-body text-white/30 text-xs mt-0.5">
                  Для смены отправим письмо с подтверждением на новый адрес
                </p>
              </div>
              <button
                onClick={() => setShowEmailForm(true)}
                className="px-4 py-2 shrink-0 bg-white/8 hover:bg-white/15 text-white/70 hover:text-white border border-white/10 rounded-xl font-body text-sm font-bold transition-all"
              >
                Изменить
              </button>
            </div>
          ) : emailSent ? (
            <div className="space-y-4">
              <div className="bg-pet-teal/10 border border-pet-teal/25 rounded-xl px-4 py-4 text-center">
                <p className="text-white font-body text-sm font-bold">Письмо отправлено</p>
                <p className="text-white/50 font-body text-xs mt-1 leading-relaxed">
                  Отправили письмо на <span className="text-white/80">{newEmail}</span>.
                  Перейдите по ссылке, чтобы подтвердить смену email.
                </p>
              </div>
              <button onClick={resetEmailForm}
                      className="w-full py-2.5 bg-white/8 hover:bg-white/15 text-white/60 rounded-xl font-body text-sm font-bold transition-all">
                Закрыть
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <Field
                label="Новый email"
                value={newEmail}
                onChange={v => { setNewEmail(v); setEmailError('') }}
                type="email"
                placeholder="new@example.com"
                error={emailError}
                autoFocus
              />
              <p className="text-white/30 text-xs font-body">
                Текущий email останется активным до подтверждения нового.
              </p>
              <div className="flex gap-2 pt-1">
                <button onClick={resetEmailForm}
                        className="flex-1 py-2.5 bg-white/8 hover:bg-white/15 text-white/60 rounded-xl font-body text-sm font-bold transition-all">
                  Отмена
                </button>
                <button onClick={handleSendEmailChange} disabled={isLoading || !newEmail.trim()}
                        className="flex-1 py-2.5 bg-pet-teal/20 hover:bg-pet-teal/30 text-pet-teal border border-pet-teal/20 rounded-xl font-body text-sm font-bold transition-all disabled:opacity-40">
                  {isLoading ? '...' : 'Отправить письмо'}
                </button>
              </div>
            </div>
          )}
        </Section>

        {/* ── Пароль ───────────────────────────────────────────────────── */}
        <Section title="Пароль">
          {passwordResetSent ? (
            <div className="space-y-4">
              <div className="bg-pet-glow/10 border border-pet-glow/25 rounded-xl px-4 py-4 text-center">
                <p className="text-white font-body text-sm font-bold">Письмо отправлено</p>
                <p className="text-white/50 font-body text-xs mt-1 leading-relaxed">
                  Инструкция по сбросу пароля отправлена на{' '}
                  <span className="text-white/80">{user.user_email}</span>.
                </p>
              </div>
              <button onClick={() => setPasswordResetSent(false)}
                      className="w-full py-2.5 bg-white/8 hover:bg-white/15 text-white/60 rounded-xl font-body text-sm font-bold transition-all">
                Закрыть
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-body text-white text-sm tracking-widest">••••••••</p>
                <p className="font-body text-white/30 text-xs mt-0.5">
                  Ссылка для сброса придёт на {user.user_email}
                </p>
                {passwordResetErr && (
                  <p className="text-red-400 text-xs font-body mt-1">{passwordResetErr}</p>
                )}
              </div>
              <button
                onClick={handlePasswordReset}
                disabled={passwordResetLoad}
                className="px-4 py-2 shrink-0 bg-white/8 hover:bg-white/15 text-white/70 hover:text-white border border-white/10 rounded-xl font-body text-sm font-bold transition-all disabled:opacity-40"
              >
                {passwordResetLoad ? '...' : 'Сбросить'}
              </button>
            </div>
          )}
        </Section>

        {/* ── Выход и удаление аккаунта ─────────────────────────────────── */}
        <Section title="Аккаунт">

          {/* Выход */}
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="font-body text-white/80 text-sm font-semibold">Выйти из аккаунта</p>
              <p className="font-body text-white/30 text-xs mt-0.5">Сессия будет завершена на этом устройстве</p>
            </div>
            <button
              onClick={handleLogout}
              disabled={logoutLoading}
              className="px-4 py-2 shrink-0 bg-white/8 hover:bg-white/15 text-white/70 hover:text-white border border-white/10 rounded-xl font-body text-sm font-bold transition-all disabled:opacity-40"
            >
              {logoutLoading ? '...' : 'Выйти'}
            </button>
          </div>

          {/* Разделитель */}
          <div className="my-4 border-t border-white/8" />

          {/* Удаление */}
          {!showDeleteConfirm ? (
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-body text-white/80 text-sm font-semibold">Удалить аккаунт</p>
                <p className="font-body text-white/30 text-xs mt-0.5">
                  Аккаунт будет удалён. Восстановление возможно в течение ограниченного времени.
                </p>
              </div>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="px-4 py-2 shrink-0 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-xl font-body text-sm font-bold transition-all"
              >
                Удалить
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
                <p className="text-red-400/90 text-sm font-body">
                  Будет удалён аккаунт <strong className="text-red-400">{user.user_login}</strong>.
                  Это действие нельзя отменить мгновенно.
                </p>
              </div>
              {deleteError && <p className="text-red-400 text-xs font-body">{deleteError}</p>}
              <div className="flex gap-2">
                <button
                  onClick={() => { setShowDeleteConfirm(false); setDeleteError('') }}
                  className="flex-1 py-2.5 bg-white/8 hover:bg-white/15 text-white/60 rounded-xl font-body text-sm font-bold transition-all"
                >
                  Отмена
                </button>
                <button
                  onClick={handleDelete}
                  disabled={isLoading}
                  className="flex-1 py-2.5 bg-red-500/70 hover:bg-red-500/90 text-white rounded-xl font-body text-sm font-bold transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {isLoading ? '...' : 'Удалить навсегда'}
                </button>
              </div>
            </div>
          )}
        </Section>

      </div>
    </div>
  )
}