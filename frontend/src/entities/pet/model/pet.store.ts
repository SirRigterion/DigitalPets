import { create } from 'zustand'
import { persist, devtools } from 'zustand/middleware'
import type {
  Pet, PetStatsDelta,
  CreatePetDto, ChatMessage, PetSchema,
  ChatMessageSchema, PetStats, PetPersonality
} from '@shared/types'
import { petApi } from '@entities/pet/api/pet.api'
import {calculateLevel} from "@shared/utils/levelSystem.ts";
import {PET_PHRASES} from "@shared/config/constants.ts";
import {getPetAgeInMinutes} from "@shared/lib/utils.ts";

function mapPet(data: PetSchema): Pet {
  const { level, currentXP, xpToNextLevel } = calculateLevel(data.pet_xp)

  const stats: PetStats = {
    hunger: data.pet_hunger,
    energy: data.pet_energy,
    happiness: data.pet_happiness,
    health: data.pet_health,
    cleanliness: data.pet_cleanliness,
  }

  return {
    id:             data.pet_id,
    name:           data.pet_name,
    type:           data.pet_species,
    personality:    data.pet_character as PetPersonality,
    customColor:    data.pet_color,

    stats,
    mood: data.pet_state,

    age: getPetAgeInMinutes(data.created_at),

    level: level,
    currentXP: currentXP,
    xpToNextLevel: xpToNextLevel,

    isSleeping:     data.pet_state === 'sleep',
    isLost:         data.is_lost,

    lastInteracted: new Date().toISOString(),
    createdAt:      data.created_at,

    phrases:        PET_PHRASES[data.pet_species] ?? [],
    currentPhrase:  PET_PHRASES[data.pet_species]?.[0] ?? '',
  }
}

function mapApiMsg(m: ChatMessageSchema): ChatMessage {
  return {
    id:        String(m.message_id),
    from:      m.message_type === 'human' ? 'user' : 'pet',
    text:      m.content,
    timestamp: m.created_at,
    isEdited:  m.is_edited,
  }
}

// ── Store ──────────────────────────────────────────────────────────────────────

interface PetStoreState {
  pet:           Pet | null
  chatId:        number | null
  chatMessages:  ChatMessage[]
  isLoading:     boolean
  isChatLoading: boolean
  error:         string | null

  fetchPet:        (id?: number) => Promise<void>
  createPet:       (dto: CreatePetDto) => Promise<void>
  applyStatChanges:(changes: PetStatsDelta) => Promise<void>
  sendChatMessage: (text: string) => Promise<void>
  loadChatHistory: () => Promise<void>
  setSleeping:     (val: boolean) => Promise<void>
  deletePet:       () => Promise<void>
  clearError:      () => void
  updatePhrase:    (msg?: string) => void
  renamePet: (name: string) => void
}

export const usePetStore = create<PetStoreState>()(
  devtools(
    persist(
      (set, get) => ({
        pet: null,
        chatId: null,
        chatMessages: [],
        isLoading: false,
        isChatLoading: false,
        error: null,

        fetchPet: async (id) => {
          set({ isLoading: true, error: null })
          try {
            const data = id
              ? await petApi.getById(id)
              : (await petApi.getMyPets())[0]

            if (data) {
              set({ pet: mapPet(data), isLoading: false })
              get().loadChatHistory()
            } else {
              set({ pet: null, isLoading: false })
            }
          } catch (err: any) {
            set({ error: err.message, isLoading: false })
          }
        },

        createPet: async (dto) => {
          set({ isLoading: true, error: null })
          try {
            const data = await petApi.create(dto)
            set({ pet: mapPet(data), isLoading: false })
          } catch (err: any) {
            set({ error: err.message, isLoading: false })
          }
        },

        applyStatChanges: async (delta) => {
          const { pet } = get()
          if (!pet) return
          try {
            const data = await petApi.updateStats(pet.id, delta)
            set({ pet: mapPet(data) })
          } catch (err: any) {
            console.error('Stats sync failed', err)
          }
        },

        loadChatHistory: async () => {
          const { pet } = get()
          if (!pet) return
          set({ isChatLoading: true })
          try {
            const chats = await petApi.getChats()
            let currentChat = chats.find(c => c.pet_id === pet.id)

            if (!currentChat) {
              currentChat = await petApi.createChat(pet.id)
            }

            if (!currentChat) {
              console.error('Не удалось создать или найти чат')
              set({ isChatLoading: false })
              return
            }

            const msgs = await petApi.getMessages(currentChat.chat_id)
            set({
              chatId: currentChat.chat_id,
              chatMessages: msgs.map(mapApiMsg),
              isChatLoading: false
            })
          } catch (err) {
            set({ isChatLoading: false })
          }
        },

        sendChatMessage: async (text) => {
          const { chatId } = get()
          if (!chatId || !text.trim()) return

          set({ isChatLoading: true })
          try {
            // Отправляем сообщение пользователя
            const userMsg = await petApi.sendMessage(chatId, text)

            // Обновляем чат локально с сообщением пользователя
            set(state => ({
              chatMessages: [...state.chatMessages, mapApiMsg(userMsg)],
            }))

            setTimeout(async () => {
              try {
                console.log(1)
                const msgs = await petApi.getMessages(chatId)
                console.log(msgs)
                console.log(2)
                const newMsgs = msgs
                  .map(mapApiMsg)
                  .filter(m => !get().chatMessages.find(cm => cm.id === m.id))

                if (newMsgs.length > 0) {
                  set(state => ({
                    chatMessages: [...state.chatMessages, ...newMsgs],
                  }))
                }
              } catch {}
            }, 3000)

          } catch (err: any) {
            set({ error: 'Ошибка отправки' })
          } finally {
            set({ isChatLoading: false })
          }
        },

        setSleeping: async (val) => {
          const { pet } = get()
          if (!pet) return
          try {
            const data = await petApi.update(pet.id, { is_sleeping: val } as any)
            set({ pet: mapPet(data) })
          } catch {}
        },

        // ── POST /pets/{id}/rename ─────────────────────────────────────────
        renamePet: async (name) => {
          const { pet } = get()
          if (!pet) return
          set({ isLoading: true })
          try {
            // PATCH /pets/{id}/name → возвращает полный PetSchema
            const data = await petApi.renamePet(pet.id, name)
            set((state) => ({
              pet: {
                ...state.pet!,
                name: data.pet_name,
              },
              isLoading: false,
            }))
            get().fetchPet()
          } catch (err) {
            set({ isLoading: false })
          }
        },

        deletePet: async () => {
          const { pet } = get()
          if (!pet) return
          try {
            await petApi.delete(pet.id)
            set({ pet: null, chatId: null, chatMessages: [] })
          } catch {}
        },

        clearError: () => set({ error: null }),

        updatePhrase: (msg?: string) => {
          if (msg) return msg

          const {pet} = get()
          if (!pet) return

          const phrases = pet.phrases ?? []
          if (phrases.length === 0) return

          let newPhrase = phrases[Math.floor(Math.random() * phrases.length)]

          if (phrases.length > 1) {
            while (newPhrase === pet.currentPhrase) {
              newPhrase = phrases[Math.floor(Math.random() * phrases.length)]
            }
          }
        },
      }),
      {
        name: 'pet-storage',
        partialize: (state) => ({ pet: state.pet }),
      }
    )
  )
)