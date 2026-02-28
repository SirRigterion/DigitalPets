import { createBrowserRouter, RouterProvider } from 'react-router'
import { HomePage } from '@pages/home/ui/HomePage'
import { PetPage } from '@pages/pet/ui/PetPage'
import { CreatePetPage } from '@pages/create-pet/ui/CreatePetPage'
import { LeaderboardPage } from '@pages/leaderboard/ui/LeaderboardPage'
import { ProfilePage } from '@pages/profile/ui/ProfilePage'
import { LoginPage } from '@pages/login/ui/LoginPage'
import { RegisterPage } from '@pages/register/ui/RegisterPage'
import { VerifyEmailPage } from '@pages/verify-email/ui/VerifyEmailPage'
import { ResetPasswordPage } from '@pages/reset-password/ui/ResetPasswordPage'
import NotFoundPage from '@pages/not-found/ui/NotFoundPage'
import { ProtectedRoute, GuestRoute } from './ProtectedRoute'

const router = createBrowserRouter([
  {
    path: '/',
    element: <HomePage />,
  },
  {
    element: <GuestRoute />,
    children: [
      { path: '/login',    element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
    ],
  },
  { path: '/verify-email',   element: <VerifyEmailPage /> },
  { path: '/reset-password', element: <ResetPasswordPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      { path: '/create',      element: <CreatePetPage /> },
      { path: '/pet',         element: <PetPage /> },
      { path: '/leaderboard', element: <LeaderboardPage /> },
      { path: '/profile',     element: <ProfilePage /> },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
])

export const AppRouter = () => {
  return <RouterProvider router={router} />
}