import { usePetStore } from '@entities/pet'
import { PET_ACTIONS } from '@shared/config/constants'
import { timeSince } from '@shared/lib/utils'
import type {PetStatsDelta} from "@shared/types";

export function useFeedPet() {
  const { pet, applyStatChanges } = usePetStore()

  const action = PET_ACTIONS.find((a) => a.type === 'feed')!

  const canFeed = (() => {
    if (!pet) return false
    if (pet.isSleeping) return false
    if (!pet.lastInteracted) return true
    return timeSince(pet.lastInteracted) >= action.cooldown
  })()

  const feed = () => {
    if (!pet || !canFeed) return

    const upData: PetStatsDelta = {
      pet_hunger:      action.statChanges.hunger,
      pet_energy:      action.statChanges.energy,
      pet_happiness:   action.statChanges.happiness,
      pet_health:      action.statChanges.health,
      pet_cleanliness: action.statChanges.cleanliness,
      pet_xp:          action.xpGain,
    }

    applyStatChanges(upData)
  }

  return { feed, canFeed, action }
}
