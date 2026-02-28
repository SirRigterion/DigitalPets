import {AppRouter} from "@app/routes/AppRouter.tsx";
import {useEffect} from "react";
import {useAuthStore} from "@entities/auth";

const App = () => {
  const fetchProfile = useAuthStore(state => state.fetchProfile)

  useEffect(() => {
    fetchProfile()
  }, [])

  return (
    <AppRouter />
  )
}

export default App
