import { useEffect, useState } from 'react'
import { weatherAPI } from '@features/weather-integration/model/weatherApi'
import type {WeatherData} from "@shared/types";

export function useWeatherAPI() {
  const [weather, setWeather] = useState<WeatherData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const fetchWeather = async () => {
      setLoading(true)
      try {
        const data = await weatherAPI.sendWeatherRequest()
        setWeather(data)
      } catch (err: any) {
        setError(err.message || 'Ошибка получения погоды')
      } finally {
        setLoading(false)
      }
    }

    fetchWeather()
  }, [])

  return { weather, error, loading }
}