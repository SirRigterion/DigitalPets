import {Navigate} from 'react-router'
import { usePetStore } from '@entities/pet'
import { useAuthStore } from '@entities/auth'

export const HomePage = () => {
  const { pet } = usePetStore()
  const { user } = useAuthStore()

  if (!user) return <Navigate to="/login" replace />
  if (pet)   return <Navigate to="/pet"    replace />

  return <Navigate to="/create" replace />
}
