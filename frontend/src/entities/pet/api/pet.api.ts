import api from '@shared/api/api.ts'
import type {
  PetSchema,
  PetStatsDelta,
  ChatMessageSchema,
  ChatSchema
} from '@shared/types'

export const petApi = {
  create: (dto: any) =>
    api.post<PetSchema>('/pets', dto).then(r => r.data),

  getById: (id: number) =>
    api.get<PetSchema>(`/pets/${id}`).then(r => r.data),

  getMyPets: () =>
    api.get<PetSchema[]>('/pets/my').then(r => r.data),

  renamePet: (petId: number, name: string) =>
    api.put(`/pets/${petId}/name`, { pet_name: name }).then(r => r.data),

  update: (id: number, data: any) =>
    api.patch<PetSchema>(`/pets/${id}`, data).then(r => r.data),

  updateStats: async (id: number, data: PetStatsDelta)  => {
    const formData = new FormData()

    data.pet_hunger != null ? formData.append("pet_hunger", String(data.pet_hunger)) : formData.append("pet_hunger", "");
    data.pet_energy != null ? formData.append("pet_energy", String(data.pet_energy)) : formData.append("pet_energy", "");
    data.pet_happiness != null ? formData.append("pet_happiness", String(data.pet_happiness)) : formData.append("pet_happiness", "");
    data.pet_cleanliness != null ? formData.append("pet_cleanliness", String(data.pet_cleanliness)) : formData.append("pet_cleanliness", "");
    data.pet_health != null ? formData.append("pet_health", String(data.pet_health)) : formData.append("pet_health", "");
    data.pet_xp != null ? formData.append("pet_xp", String(data.pet_xp)) : formData.append("pet_xp", "");

    return await api.patch<PetSchema>(`/pets/${id}`, formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded"}
    }).then(r => r.data)
  },

  delete: (id: number) =>
    api.delete(`/pets/${id}`),

  getChats: (limit?: number, offset?: number) =>
    api.get<ChatSchema[]>('/chats', {
      params: {limit, offset}
    }).then(r => r.data),

  createChat: (petId: number) =>
    api.post('/chats',{ pet_id: petId }).then(r => r.data),

  getMessages: (chatId: number, limit?: number, offset?: number) =>
    api.get<ChatMessageSchema[]>(`/chats/messages/chats/${chatId}/messages`, {
      params: {limit, offset}
    }).then(r => r.data),

  sendMessage: (chatId: number, content: string) =>
    api.post<ChatMessageSchema>(`/chats/messages/chats/${chatId}/messages`, { content }).then(r => r.data),
}