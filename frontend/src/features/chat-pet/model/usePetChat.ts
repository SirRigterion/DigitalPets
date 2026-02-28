import { useState, useCallback, useEffect, useRef } from 'react'
import { usePetStore } from '@entities/pet'

export function usePetChat() {
  const { loadChatHistory, sendChatMessage, isChatLoading } = usePetStore()
  const [error, setError] = useState<string | null>(null)
  const [inputValue, setInputValue] = useState('')
  const initialized = useRef(false)

  useEffect(() => {
    if (initialized.current) return
    initialized.current = true
    loadChatHistory()
  }, [loadChatHistory])

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || isChatLoading) return
      setInputValue('')
      setError(null)
      try {
        await sendChatMessage(trimmed)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Ошибка отправки')
      }
    },
    [isChatLoading, sendChatMessage]
  )

  return { inputValue, setInputValue, sendMessage, isTyping: isChatLoading, error }
}