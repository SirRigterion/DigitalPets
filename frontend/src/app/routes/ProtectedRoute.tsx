import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuthStore } from '@entities/auth'
import { usePetStore } from '@entities/pet'
import { Header } from '@widgets/header/ui/Header'

const InitLoader = () => (
  <div className="min-h-screen bg-pet-bg flex items-center justify-center">
    <div className="fixed inset-0 overflow-hidden pointer-events-none">
      <div className="absolute -top-32 -left-32 w-96 h-96 bg-pet-glow/10 rounded-full blur-3xl animate-pulse-slow" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-pet-teal/10 rounded-full blur-3xl animate-pulse-slow" />
    </div>
    <div className="relative flex flex-col items-center gap-4">
      <div className="w-10 h-10 border-2 border-white/15 border-t-pet-glow rounded-full animate-spin" />
      <p className="font-body text-white/30 text-sm">Загрузка...</p>
    </div>
  </div>
)

export const ProtectedRoute = () => {
  const { user, isInitialized } = useAuthStore()
  const { pet } = usePetStore()
  const location = useLocation()

  if (!isInitialized) return <InitLoader />

  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  const requiresPet = location.pathname === '/pet'
  if (requiresPet && !pet) {
    return <Navigate to="/create" replace />
  }

  const requiresCreate = location.pathname === '/create'
  if (requiresCreate && pet) {
    return <Navigate to='/pet' />
  }

  return (
    <div>
      <Header />
      <main className="h-[calc(100vh-60px)] overflow-y-auto"> {/*Вычитаем header из main*/}
        <Outlet />
      </main>
    </div>
  )
}

export const GuestRoute = () => {
  const { user, isInitialized } = useAuthStore()
  const { pet } = usePetStore()

  if (!isInitialized) return <InitLoader />

  if (user) {
    return <Navigate to={pet ? '/pet' : '/create'} replace />
  }

  return <Outlet />
}
