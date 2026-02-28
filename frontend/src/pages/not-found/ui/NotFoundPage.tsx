import React from 'react'
import { Link } from 'react-router'

const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-pet-bg flex flex-col items-center justify-center px-4 text-center">
      <div className="animate-float text-7xl mb-6">🐾</div>
      <h1 className="font-display text-6xl text-white mb-2">
        4<span className="text-pet-glow">0</span>4
      </h1>
      <p className="font-body text-white/50 text-lg mb-8">
        Питомец не смог найти эту страницу...
      </p>
      <Link
        to="/"
        className="px-6 py-3 bg-pet-glow/80 hover:bg-pet-glow text-white font-body font-bold rounded-2xl transition-all duration-200 active:scale-95"
      >
        Вернуться домой
      </Link>
    </div>
  )
}

export default NotFoundPage
