export const BASE_XP = 100

export interface LevelData {
  level: number
  currentXP: number
  xpToNextLevel: number
}

export function calculateLevel(totalXP: number): LevelData {
  let level = 1
  let xpLeft = totalXP
  let xpNeeded = BASE_XP * level

  while (xpLeft >= xpNeeded) {
    xpLeft -= xpNeeded
    level++
    xpNeeded = BASE_XP * level
  }

  return {
    level,
    currentXP: xpLeft,
    xpToNextLevel: xpNeeded,
  }
}