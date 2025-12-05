// react/src/components/PlaylistManager.jsx

import React from 'react';
import PlaylistCard from './PlaylistCard';

export default function PlaylistManager({
  userPlaylists,
  onTriggerCreateNewPlaylist,
  onLoadPlaylist,
  onLoadPlaylistFromTrack,
}) {

  const handlePlaylistCardClick = (playlistId) => {
    onLoadPlaylist(playlistId);
  };

  const sortedPlaylists = [...userPlaylists].sort((a, b) => {
    if (a.name === 'Мне нравится') return -1;
    if (b.name === 'Мне нравится') return 1;
    return 0;
  });

  return (
    <div className="playlist-manager-section">
      <h3>Мои плейлисты</h3>
      <div className="playlist-grid">
        {(sortedPlaylists || []).map(playlist => (
          <PlaylistCard 
            key={playlist.id}
            playlist={playlist}
            onClick={handlePlaylistCardClick}
            onLoadFromTrack={onLoadPlaylistFromTrack}
          />
        ))}
        <div className="playlist-card create-new-card" onClick={onTriggerCreateNewPlaylist}>
          <h4>+ Создать новый</h4>
        </div>
      </div>
    </div>
  );
}
