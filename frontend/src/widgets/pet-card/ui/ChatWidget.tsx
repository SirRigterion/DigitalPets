import React, { useRef, useEffect } from 'react'
import { usePetStore } from '@entities/pet'
import { usePetChat } from '@features/chat-pet/model/usePetChat'
import { cn } from '@shared/lib/utils'

export const ChatWidget: React.FC = () => {
  const { chatMessages } = usePetStore()
  const { inputValue, setInputValue, sendMessage, isTyping, error } = usePetChat()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages, isTyping])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendMessage(inputValue)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(inputValue)
    }
  }

  return (
    <div className="flex flex-col bg-white/5 rounded-2xl border border-white/10 overflow-hidden"
         style={{ height: '320px' }}>

      {/* Сообщения */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {chatMessages.length === 0 && !isTyping && (
          <div className="flex items-center justify-center h-full">
            <p className="text-center text-white/25 text-sm font-body">
              Напиши что-нибудь своему питомцу
            </p>
          </div>
        )}

        {chatMessages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              'flex gap-2 animate-slideUp',
              msg.from === 'user' ? 'flex-row-reverse' : 'flex-row'
            )}
          >
            {/* Аватарка питомца */}
            {msg.from === 'pet' && (
              <div className="w-6 h-6 rounded-full bg-pet-glow/20 border border-pet-glow/30 flex items-center justify-center shrink-0 mt-0.5">
                <span className="text-xs">🐾</span>
              </div>
            )}

            <div className={cn(
              'max-w-[78%] px-3 py-2 rounded-2xl text-sm font-body leading-relaxed',
              msg.from === 'user'
                ? 'bg-pet-glow/25 text-white rounded-tr-sm'
                : 'bg-white/10 text-white/90 rounded-tl-sm'
            )}>
              {msg.text}
              {msg.isEdited && (
                <span className="text-white/30 text-xs ml-1">(изм.)</span>
              )}
            </div>
          </div>
        ))}

        {/* Индикатор печати */}
        {isTyping && (
          <div className="flex gap-2 animate-fadeIn">
            <div className="w-6 h-6 rounded-full bg-pet-glow/20 border border-pet-glow/30 flex items-center justify-center shrink-0 mt-0.5">
              <span className="text-xs">🐾</span>
            </div>
            <div className="bg-white/10 px-4 py-2.5 rounded-2xl rounded-tl-sm">
              <span className="flex gap-1 items-center">
                <span className="w-1.5 h-1.5 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: '120ms' }} />
                <span className="w-1.5 h-1.5 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: '240ms' }} />
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Ошибка */}
      {error && (
        <div className="px-3 py-1.5 bg-red-500/10 border-t border-red-500/20">
          <p className="text-red-400 text-xs font-body">{error}</p>
        </div>
      )}

      {/* Инпут */}
      <form onSubmit={handleSubmit} className="p-2.5 border-t border-white/10 flex gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={e => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Написать питомцу..."
          maxLength={500}
          disabled={isTyping}
          className={cn(
            'flex-1 bg-white/8 border border-white/10 rounded-xl px-3 py-2 text-sm text-white',
            'placeholder-white/25 font-body focus:outline-none focus:border-pet-glow/40',
            'transition-colors disabled:opacity-50'
          )}
        />
        <button
          type="submit"
          disabled={!inputValue.trim() || isTyping}
          className={cn(
            'w-9 h-9 flex items-center justify-center rounded-xl font-bold transition-all duration-200',
            'bg-pet-glow/70 hover:bg-pet-glow text-white',
            'disabled:opacity-30 disabled:cursor-not-allowed active:scale-95'
          )}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </form>
    </div>
  )
}