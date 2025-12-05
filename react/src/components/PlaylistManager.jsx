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

  return (
    <div className="playlist-manager-section">
      <h3>Мои плейлисты</h3>
      <div className="playlist-grid">
        {(userPlaylists || []).map(playlist => (
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
