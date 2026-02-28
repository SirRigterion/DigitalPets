import React from 'react'
import type { PetType, PetStateValue } from '@shared/types'
import { cn } from '@shared/lib/utils'

interface PetAvatarProps {
  type:        PetType
  mood:        PetStateValue
  color?:      string
  size?:       'sm' | 'md' | 'lg' | 'xl'
  className?:  string
  isSleeping?: boolean
  static?:     boolean
}

const SIZE_MAP = { sm: 64, md: 120, lg: 180, xl: 240 }

function adjustColor(hex: string, factor = 0.3): string {
  hex = hex.replace('#', '')
  const r = parseInt(hex.substring(0, 2), 16)
  const g = parseInt(hex.substring(2, 4), 16)
  const b = parseInt(hex.substring(4, 6), 16)
  const newR = Math.min(255, Math.max(0, r + (255 - r) * factor))
  const newG = Math.min(255, Math.max(0, g + (255 - g) * factor))
  const newB = Math.min(255, Math.max(0, b + (255 - b) * factor))
  return `#${Math.round(newR).toString(16).padStart(2, '0')}${Math.round(newG).toString(16).padStart(2, '0')}${Math.round(newB).toString(16).padStart(2, '0')}`
}

function MoodEyes({ mood }: { mood: PetStateValue }) {
  switch (mood) {
    case 'sleep':
      return (
        <g stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round">
          <path d="M 28 48 Q 35 43 42 48" />
          <path d="M 58 48 Q 65 43 72 48" />
        </g>
      )
    case 'sick1': // Легкое недомогание (веки прикрыты)
      return (
        <g fill="currentColor">
          <ellipse cx="35" cy="48" rx="6" ry="4" />
          <ellipse cx="65" cy="48" rx="6" ry="4" />
          <path d="M 28 42 Q 35 40 42 42" stroke="currentColor" strokeWidth="2" fill="none" />
          <path d="M 58 42 Q 65 40 72 42" stroke="currentColor" strokeWidth="2" fill="none" />
        </g>
      )
    case 'sick2': // Грустный/болезненный
      return (
        <g fill="currentColor">
          <ellipse cx="35" cy="48" rx="6" ry="4" />
          <ellipse cx="65" cy="48" rx="6" ry="4" />
          <path d="M 28 42 Q 35 40 42 42" stroke="currentColor" strokeWidth="2" fill="none" />
          <path d="M 58 42 Q 65 40 72 42" stroke="currentColor" strokeWidth="2" fill="none" />
        </g>
      )
    case 'sick3': // Плохо совсем (крестики)
      return (
        <g stroke="currentColor" strokeWidth="3" strokeLinecap="round">
          <line x1="30" y1="42" x2="40" y2="52" /><line x1="40" y1="42" x2="30" y2="52" />
          <line x1="60" y1="42" x2="70" y2="52" /><line x1="70" y1="42" x2="60" y2="52" />
        </g>
      )
    case 'play': // Эйфория/игра
      return (
        <g stroke="currentColor" strokeWidth="4" fill="none" strokeLinecap="round">
          <path d="M 28 48 Q 35 35 42 48" />
          <path d="M 58 48 Q 65 35 72 48" />
          <circle cx="20" cy="35" r="2" fill="#fbbf24" stroke="none" className="animate-pulse" />
          <circle cx="80" cy="30" r="1.5" fill="#fbbf24" stroke="none" className="animate-pulse" />
        </g>
      )
    case 'sad':
      return (
        <g fill="currentColor">
          <ellipse cx="35" cy="48" rx="5" ry="6" />
          <ellipse cx="65" cy="48" rx="5" ry="6" />
          <g
            transform="translate(30 58) scale(0.7)"
            fill="#60a5fa"
          >
            <path d="M 6 -7 C 6 -3 14 4 6 5 C -2 4 6 -3 6 -7" />
          </g>
        </g>
      )
    default: // 'neutral'
      return (
        <g fill="currentColor">
          <circle cx="35" cy="45" r="6" />
          <circle cx="65" cy="45" r="6" />
          <circle cx="37" cy="42" r="2" fill="white" />
          <circle cx="67" cy="42" r="2" fill="white" />
        </g>
      )
  }
}

function MoodMouth({ mood }: { mood: PetStateValue }) {
  switch (mood) {
    case 'play':
      return (
        <g>
          <path d="M 40 60 Q 50 75 60 60 Z" fill="#e11d48" />
          <path d="M 40 60 Q 50 75 60 60" stroke="currentColor" strokeWidth="2" fill="none" />
        </g>
      )
    case 'neutral':
      return <path d="M 40 58 Q 50 63 60 58" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    case 'sad':
    case 'sick1':
      return <path d="M 42 66 Q 50 65 58 66" stroke="currentColor" strokeWidth="2.5" fill="none" strokeLinecap="round" />
    case 'sick2':
      return <path d="M 42 66 Q 50 58 58 66" stroke="currentColor" strokeWidth="2.5" fill="none" strokeLinecap="round" />
    case 'sick3':
      return <path d="M 42 66 Q 50 58 58 66" stroke="currentColor" strokeWidth="2.5" fill="none" strokeLinecap="round" />
    case 'sleep':
      return <circle cx="50" cy="64" r="3" fill="none" stroke="currentColor" strokeWidth="2" />
    default:
      return <path d="M 45 62 L 55 62" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  }
}

function PetBody({ type, color }: { type: PetType; color: string }) {
  const lightColor = adjustColor(color, 0.4)
  const darkColor  = adjustColor(color, -0.2)

  const BaseBody = () => (
    <>
      <ellipse cx="50" cy="55" rx="35" ry="32" fill={color} />
      <ellipse cx="50" cy="65" rx="20" ry="12" fill={lightColor} opacity="0.7" />
    </>
  )

  switch (type) {
    case 'cat':
      return (
        <>
          <path d="M 80 60 Q 95 40 85 25" stroke={color} strokeWidth="8" fill="none" strokeLinecap="round" />
          <polygon points="20,39 15,10 38,25" fill={color} stroke={color} strokeLinejoin="round" />
          <polygon points="23,32 19,16 34,26" fill={lightColor} />
          <polygon points="80,39 85,10 62,25" fill={color} stroke={color} strokeLinejoin="round" />
          <polygon points="77,32 81,16 66,26" fill={lightColor} />
          <BaseBody />
        </>
      )
    case 'dog':
      return (
        <>
          <path d="M 75 70 Q 90 75 85 60" stroke={color} strokeWidth="8" fill="none" strokeLinecap="round" />
          <ellipse cx="18" cy="45" rx="10" ry="20" fill={darkColor} transform="rotate(15 18 45)" />
          <ellipse cx="82" cy="45" rx="10" ry="20" fill={darkColor} transform="rotate(-15 82 45)" />
          <BaseBody />
          <ellipse cx="35" cy="45" rx="12" ry="14" fill={darkColor} opacity="0.3" />
        </>
      )
    case 'rabbit':
      return (
        <>
          <circle cx="73" cy="75" r="10" fill="white" opacity="0.9" />
          <ellipse cx="35" cy="22" rx="8" ry="22" fill={color} />
          <ellipse cx="35" cy="24" rx="4" ry="17" fill={lightColor} />
          <ellipse cx="65" cy="22" rx="8" ry="22" fill={color} />
          <ellipse cx="65" cy="24" rx="4" ry="17" fill={lightColor} />
          <BaseBody />
        </>
      )
    case 'fox':
      return (
        <>
          <path d="M 75 65 Q 106 50 90 20 Q 80 40 70 50" fill={darkColor} />
          <path d="M 95 34 Q 94 28 90 20 Q 86 27 84 31" fill="white" />
          <polygon points="20,39 25,5 40,25" fill={darkColor} stroke={darkColor} strokeLinejoin="round" />
          <polygon points="80,39 75,5 60,25" fill={darkColor} stroke={darkColor} strokeLinejoin="round" />
          <polygon points="25,39 25,5 40,25" fill={lightColor} stroke={lightColor} strokeLinejoin="round" />
          <polygon points="75,34 75,5 60,25" fill={lightColor} stroke={lightColor} strokeLinejoin="round" />
          <polygon points="15,55 50,55 50,85" fill={color} />
          <polygon points="85,55 50,55 50,85" fill={color} />
          <BaseBody />
          <path d="M 15 55 Q 50 80 85 55 Q 50 105 15 55" fill="white" opacity="0.9"/>
        </>
      )
    case 'dragon':
      return (
        <>
          <path d="M 25 45 Q 5 25 15 15 Q 25 30 35 45" fill={darkColor} />
          <path d="M 75 45 Q 95 25 85 15 Q 75 30 65 45" fill={darkColor} />
          <polygon points="88,74 96,70 94,80" fill={darkColor} />
          <polygon points="82,70 93,66 91,75" fill={darkColor} />
          <polygon points="81,66 88,62 86,73" fill={darkColor} />
          <path d="M 75 65 Q 90 71 92 77" stroke={color} strokeWidth="8" fill="none" strokeLinecap="round" />
          <polygon points="35,27 30,10 47,27" fill={lightColor} />
          <polygon points="65,27 70,10 53,27" fill={lightColor} />
          <BaseBody />
        </>
      )
    default:
      return <BaseBody />
  }
}

export const PetAvatar: React.FC<PetAvatarProps> = ({
  type,
  mood,
  color = '#3b82f6',
  size = 'md',
  className,
  isSleeping,
  static: isStatic = false,
}) => {
  const px = SIZE_MAP[size]
  const actualMood = isSleeping ? 'sleep' : mood

/*  const isSick =
    actualMood === 'sick1' ||
    actualMood === 'sick2' ||
    actualMood === 'sick3'
  const isSad = actualMood === "sad"*/

  const isPlay = actualMood === 'play'
  const isNeutral = actualMood === "neutral"
  const isSleep = actualMood === "sleep"

  // Динамические эффекты в зависимости от стадии болезни
  const getFilter = () => {
    if (isStatic) return undefined
    switch (actualMood) {
      case 'sick1': return 'saturate(0.8)'
      case 'sick2': return 'saturate(0.6) hue-rotate(-10deg)'
      case 'sick3': return 'saturate(0.4) hue-rotate(-25deg) contrast(1.1)'
      default: return undefined
    }
  }

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)}>
      <svg
        width={px} height={px} viewBox="-10 -10 120 120" fill="none"
        style={{ filter: getFilter(), transition: 'all 1s ease' }}
      >
        <ellipse cx="50" cy="92" rx="25" ry="4" fill="black" opacity="0.1" />

        <g
          className={cn(
            !isStatic && isNeutral && 'animate-breathe',
            !isStatic && isPlay && "animate-wiggle",
            !isStatic && isSleep && "opacity-50"
          )}
          style={{ transformOrigin: '50px 90px' }}
        >
          <PetBody type={type} color={color} />

          <g color="#1e293b">
            <MoodEyes mood={actualMood} />
            <MoodMouth mood={actualMood} />
          </g>
        </g>

        {!isStatic && actualMood === 'sleep' && (
          <g className="animate-pulse">
            <text x="75" y="30" fontSize="12" fill="#64748b" fontWeight="bold">Z</text>
            <text x="85" y="20" fontSize="16" fill="#64748b" fontWeight="bold">Z</text>
          </g>
        )}

        {/* Спец-эффекты для болезни */}
        {actualMood === 'sick3' && (
          <path d="M 20 15 L 20 25 M 15 20 L 25 20" stroke="#ef4444" strokeWidth="2" />
        )}
      </svg>
    </div>
  )
}