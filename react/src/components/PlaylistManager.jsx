// react/src/components/PlaylistManager.jsx
import React from 'react';
// import axios from 'axios'; // axios здесь не нужен, если все API-вызовы обрабатываются через колбэки

const formatTrackName = (filename) => {
  if (!filename) return '';
  return filename.split('\\').pop();
};

export default function PlaylistManager({ userId, onPlaylistTrackSelect, userPlaylists, onTriggerCreateNewPlaylist, fetchPlaylists }) {

  // Функция, вызываемая при клике на карточку плейлиста
  const handlePlaylistCardClick = (playlistId) => {
    // В данном контексте, "onPlaylistTrackSelect" из PlayerView используется для "открытия" плейлиста,
    // то есть, он загружает треки этого плейлиста в основной плеер.
    onPlaylistTrackSelect(playlistId); // PlayerView должен обработать это
  };


  return (
    <div className="playlist-manager-section">
      <h3>Мои плейлисты</h3>
      <div className="playlist-grid">
        {(userPlaylists || []).map(playlist => ( // Убедимся, что userPlaylists - это массив
          <div key={playlist.id} className="playlist-card" onClick={() => handlePlaylistCardClick(playlist.id)}>
            <h4>{playlist.name} ({playlist.track_count})</h4>
            <div className="playlist-card-tracks">
              {/* Здесь будут отображаться 3 трека-превью.
                  Для этого API /api/playlists должен возвращать preview_tracks */}
              <p>Превью треков...</p> {/* Пока заглушка */}
            </div>
          </div>
        ))}
        <div className="playlist-card create-new-card" onClick={onTriggerCreateNewPlaylist}> {/* Вызываем колбэк для открытия модалки */}
          <h4>+ Создать новый</h4>
        </div>
      </div>
    </div>
  );
}
