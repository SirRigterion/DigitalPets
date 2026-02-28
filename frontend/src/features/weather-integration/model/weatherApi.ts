import api from "@shared/api/api.ts";

export const weatherAPI = {
  sendWeatherRequest: async () => {
    const position = await new Promise<GeolocationPosition>((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Геолокация недоступна'))
        return
      }

      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 5000,
      })
    })

    const { latitude, longitude } = position.coords

    const response = await api.post('/weather/', {
      latitude,
      longitude,
    })

    return response.data
  },

  sendMeLocation: () => {
  //
  }
}