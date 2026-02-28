// ─────────────────────────────────────────────────────────────────────────────
// SHARED TYPES
// ─────────────────────────────────────────────────────────────────────────────

// ══════════════════════════════════════════════════════════════════════════════
// 👤 AUTH & USER
// ══════════════════════════════════════════════════════════════════════════════

// Точное зеркало ответа GET /users/ от бэкенда
export interface UserProfile {
  user_id:        number
  user_login:     string
  user_full_name: string
  user_email:     string
  user_avatar:    string | null   // имя файла → /images/private/{user_avatar}
  role_id:        number
  registered_at:  string          // ISO 8601
  is_deleted:     boolean
  status:         'registered' | 'active' | 'banned'
  ban_reason:     string | null
  banned_at:      string | null
}

// DTO для регистрации → POST /auth/register
export interface RegisterUser {
  user_login:     string
  user_full_name: string
  user_email:     string
  user_password:  string          // min 8
}

// DTO для входа → POST /auth/login
export interface LoginUser {
  user_identifier: string         // login или email
  password:        string
}

// ══════════════════════════════════════════════════════════════════════════════
// 🐾 PET
// ══════════════════════════════════════════════════════════════════════════════

export type PetType        = 'cat' | 'dog' | 'rabbit' | 'dragon' | 'fox'
export type PetPersonality = 'playful' | 'lazy' | 'curious' | 'shy' | 'energetic'

export interface PetStats {
  hunger:      number
  energy:      number
  happiness:   number
  health:      number
  cleanliness: number
}


export interface PetStatsDelta {
  pet_hunger?: number
  pet_energy?: number
  pet_happiness?: number
  pet_health?: number
  pet_cleanliness?: number
  pet_xp?: number
}

export type PetCharacter  = 'playful' | 'lazy' | 'curious' | 'shy' | 'energetic'

export type PetStateValue = 'neutral' | "sad" | 'sleep' | 'sick1' | 'sick2' | 'sick3' | 'play'

export const PET_FEATURES = [
  "normal",
  "rain_lover",
  "cold_lover",
  "day_lover",
  "hot_hater",
  "sun_hater",
  "rain_hater"
] as const

export type PetFeature = typeof PET_FEATURES[number]

export interface PetSchema {
  pet_id:          number
  pet_name:        string
  pet_species:     PetType
  pet_color:       string
  pet_character:   PetCharacter  // Убрал ?, так как в базе он обычно есть
  pet_feature:     PetFeature        // В доке это строка
  pet_state:       PetStateValue // Используем строгий тип вместо string
  pet_hunger:      number
  pet_energy:      number
  pet_happiness:   number
  pet_cleanliness: number
  pet_health:      number
  pet_xp:          number
  created_at:      string
  last_updated?:   string
  owner_id:        number
  is_deleted:      boolean
  is_lost:         boolean
  lost_at?:        string
  search_token_created_at: string
}

/**
 * Pet — объект, который используется внутри приложения (camelCase)
 */
export interface Pet {
  id:             number // Приводим к числу, как в БД
  name:           string
  type:           PetType
  personality:    PetPersonality
  customColor:    string
  stats:          PetStats
  mood:           PetStateValue
  level:          number
  currentXP: number
  xpToNextLevel: number
  age: number
  isSleeping:     boolean
  isLost:         boolean
  lastInteracted: string
  createdAt:      string
  phrases:        string[]
  currentPhrase:  string
}

export interface CreatePetDto {
  pet_name:      string
  pet_species:   PetType
  pet_character: PetPersonality
  pet_color:     string
  pet_feature: PetFeature;
}

export interface PetStatsDelta {
  pet_hunger?:      number
  pet_energy?:      number
  pet_happiness?:   number
  pet_health?:      number
  pet_cleanliness?: number
  pet_xp?:          number
}
// ══════════════════════════════════════════════════════════════════════════════
// 🎮 PET ACTIONS
// ══════════════════════════════════════════════════════════════════════════════

export type PetActionType = 'feed' | 'play' | 'heal' | 'clean'

export interface PetAction {
  id:          string
  type:        PetActionType
  label:       string
  emoji:       string
  cooldown:    number
  statChanges: Partial<PetStats>
  xpGain:      number
  description: string
}

// ══════════════════════════════════════════════════════════════════════════════
// 💬 CHAT
// ══════════════════════════════════════════════════════════════════════════════

export interface ChatSchema {
  chat_id: number
  pet_id: number
  user_id: number
  created_at: string
  last_message_at: string | null
  is_unread: boolean
}

export interface ChatMessage {
  id:        string
  from:      'user' | 'pet'
  text:      string
  timestamp: string
  isEdited?: boolean
}

// Ответ POST /chats/messages/chats/{chat_id}/messages
export interface SendMessageResponse {
  human_message: {
    message_id:   number
    message_type: 'human'
    content:      string
    created_at:   string
    is_edited:    boolean
  }
  ai_message: {
    message_id:   number
    message_type: 'ai'
    content:      string
    created_at:   string
    is_edited:    boolean
  }
}

// Элемент из GET /chats/messages/chats/{chat_id}/messages
export interface ChatMessageSchema {
  message_id:   number
  chat_id: number
  message_type: 'human' | 'ai'
  content:      string
  created_at:   string
  updated_at: string
  is_edited:    boolean
  is_deleted: boolean
}

// ══════════════════════════════════════════════════════════════════════════════
// 🌦 WEATHER
// ══════════════════════════════════════════════════════════════════════════════

export interface WeatherData {
  temp:        number
  description: string
  icon:        string
  city:        string
  humidity:    number
}

export interface WeatherMoodEffect {
  happiness: number
  energy:    number
  label:     string
}


// ══════════════════════════════════════════════════════════════════════════════
// 🌐 API — общие
// ══════════════════════════════════════════════════════════════════════════════

export interface ApiResponse<T> {
  data:     T
  success:  boolean
  message?: string
}

export interface ValidationError {
  detail: Array<{
    loc:  [string, string]
    msg:  string
    type: string
  }>
}

export interface PaginationParams {
  limit?:  number
  offset?: number
}

