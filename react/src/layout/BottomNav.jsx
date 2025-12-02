// react/src/layout/BottomNav.jsx
import React from 'react';
// Иконки можно заменить на реальные SVG-иконки для лучшего вида
const PlayerIcon = () => <span>▶️</span>;
const MusicIcon = () => <span>🎵</span>;
const SettingsIcon = () => <span>⚙️</span>;

export default function BottomNav({ activeView, setActiveView }) {
  return (
    <nav className="bottom-nav">
      <button 
        className={`nav-button ${activeView === 'player' ? 'active' : ''}`}
        onClick={() => setActiveView('player')}
      >
        <PlayerIcon />
        <span>Плеер</span>
      </button>
      <button 
        className={`nav-button ${activeView === 'all-songs' ? 'active' : ''}`}
        onClick={() => setActiveView('all-songs')}
      >
        <MusicIcon />
        <span>Все песни</span>
      </button>
      <button 
        className="nav-button"
        onClick={() => alert('Настройки еще не реализованы!')}
      >
        <SettingsIcon />
        <span>Настройки</span>
      </button>
    </nav>
  );
}