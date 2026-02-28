import axios from 'axios'

export class EmailNotVerifiedError extends Error {
  constructor() {
    super('Подтвердите email перед входом')
    this.name = 'EmailNotVerifiedError'
  }
}

// Проверяем, является ли ответ ошибкой "email не подтверждён"
function isEmailNotVerified(data: unknown): boolean {
  if (!data || typeof data !== 'object') return false
  const d = data as Record<string, unknown>

  // Вариант 1: { "error": { "code": 403, "message": "Подтвердите email перед входом" } }
  if (d.error && typeof d.error === 'object') {
    const err = d.error as Record<string, unknown>
    if (err.code === 403 && typeof err.message === 'string') {
      const msg = err.message.toLowerCase()
      if (msg.includes('подтвердите email') || msg.includes('подтвердите почту') || msg.includes('email')) {
        return true
      }
    }
  }

  // Вариант 2: { "detail": "Подтвердите почту." }
  if (typeof d.detail === 'string') {
    const msg = d.detail.toLowerCase()
    if (msg.includes('подтвердите') || msg.includes('подтвердите почту') || msg.includes('verify')) {
      return true
    }
  }

  return false
}

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api/v1",
  timeout: 10000,
  withCredentials: true,
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const data = error.response?.data

    // Сначала проверяем на "email не подтверждён" — выбрасываем специальную ошибку
    if (isEmailNotVerified(data)) {
      return Promise.reject(new EmailNotVerifiedError())
    }

    // 422 Validation error
    if (error.response?.status === 422) {
      const detail = data?.detail
      if (Array.isArray(detail) && detail.length > 0) {
        error.message = detail[0].msg
      }
    }
    // Ошибка из поля error.message
    else if (data?.error?.message) {
      error.message = data.error.message
    }
    // Ошибка из поля message
    else if (data?.message) {
      error.message = data.message
    }
    // Ошибка из поля detail (строка)
    else if (typeof data?.detail === 'string') {
      error.message = data.detail
    }

    return Promise.reject(error)
  }
)

export default api