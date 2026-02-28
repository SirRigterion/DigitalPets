import { create } from 'zustand'
import type {
  UserProfile,
  LoginUser, RegisterUser
} from '@shared/types'
import api, {/*EmailNotVerifiedError*/} from '@shared/api/api.ts';

function parseError(err: unknown): string {
  if (err instanceof Error) return err.message
  return 'Произошла ошибка'
}

interface AuthState {
  user: UserProfile | null
  isLoading: boolean
  isInitialized: boolean
  error: string | null

  // Auth
  login: (user: LoginUser) => Promise<void>
  register: (user: RegisterUser) => Promise<void>
  logout: () => Promise<void>
  fetchProfile: () => Promise<void>
  clearError:   () => void

  // Профиль
  updateUsername: (userName: string) => Promise<void>
  updateFullName: (fullName: string) => Promise<void>
  updateEmail: (email: string) => Promise<void>
  uploadAvatar: (file: File) => Promise<void>
  requestPasswordReset: () => Promise<void>
  deleteAccount: () => Promise<void>
}

export const useAuthStore = create<AuthState>()((set, get) => ({
      user: null,
      isLoading: false,
      isInitialized: false,
      error: null,

      // ── POST /auth/login ──────────────────────────────────────────────
      login: async (user) => {
        set({ isLoading: true, error: null })
        try {
          await api.post('/auth/login', user)

          const { data } = await api.get<UserProfile>('/users/')
          set({ user: data, isLoading: false })
        } catch (err) {
          // if (err instanceof EmailNotVerifiedError) throw err
          set({ error: parseError(err), isLoading: false })
          throw err
        }
      },

      // ── POST /auth/register ───────────────────────────────────────────
      register: async (user) => {
        set({ isLoading: true, error: null })
        try {
          await api.post('/auth/register', user)
          set({ isLoading: false })
        } catch (err) {
          // if (err instanceof EmailNotVerifiedError) throw err
          set({ error: parseError(err), isLoading: false })
          throw err
        }
      },

      // ── POST /auth/logout ─────────────────────────────────────────────
      logout: async () => {
        try {
          await api.post('/auth/logout')
        } catch {}
        set({ user: null })
      },

      // ── GET /users/ — восстановить сессию из cookie ───────────────────
      fetchProfile: async () => {
        try {
          set({isLoading: true})
          const { data } = await api.get<UserProfile>('/users/')
          set({ user: data })
        } catch {
          set({ user: null })
        } finally {
          set({isLoading: false, isInitialized: true})
        }
      },

      clearError: () => set({ error: null }),

      // ── PATCH /users/ — имя ───────────────────────────────────────────
  updateUsername: async (username) => {
    set({ isLoading: true })
    try {
      const form = new FormData()
      form.append('user_login', username)
      const { data } = await api.patch<UserProfile>('/users/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      set({ user: data, isLoading: false })
    } catch (err) {
      set({ isLoading: false })
      throw new Error(parseError(err))
    }
  },

  // ── PATCH /users/ — полное имя ──────────────────────────────────────────
  updateFullName: async (fullName) => {
    set({ isLoading: true })
    try {
      const form = new FormData()
      form.append('user_full_name', fullName)
      const { data } = await api.patch<UserProfile>('/users/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      set({ user: data, isLoading: false })
    } catch (err) {
      set({ isLoading: false })
      throw new Error(parseError(err))
    }
  },

  // ── PATCH /users/ — email ───────────────────────────────────────────────
  updateEmail: async (email) => {
    set({ isLoading: true })
    try {
      const form = new FormData()
      form.append('user_email', email)
      const { data } = await api.patch<UserProfile>('/users/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      set({ user: data, isLoading: false })
    } catch (err) {
      set({ isLoading: false })
      throw new Error(parseError(err))
    }
  },

  // ── PATCH /users/ — аватарка ────────────────────────────────────────────
  uploadAvatar: async (file) => {
    set({ isLoading: true })
    try {
      const form = new FormData()
      form.append('photo', file)
      const { data } = await api.patch<UserProfile>('/users/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      set({ user: data, isLoading: false })
    } catch (err) {
      set({ isLoading: false })
      throw new Error(parseError(err))
    }
  },

  // ── POST /users/reset-password/request ──────────────────────────────────
  requestPasswordReset: async () => {
    if (!get().user) return
    set({ isLoading: true })
    try {
      await api.post('/users/reset-password/request')
      set({ isLoading: false })
    } catch (err) {
      set({ isLoading: false })
      throw new Error(parseError(err))
    }
  },

  // ── DELETE /users/ ───────────────────────────────────────────────────────
  deleteAccount: async () => {
    set({ isLoading: true })
    try {
      await api.delete('/users/')
      set({ user: null, isLoading: false })
    } catch (err) {
      set({ isLoading: false })
      throw new Error(parseError(err))
    }
  },
}))