// react/src/components/PlaylistManager.jsx

import React from 'react';

export default function PlaylistManager({
  userPlaylists,
  onTriggerCreateNewPlaylist,
  onLoadPlaylist,
  onLoadPlaylistFromTrack,
}) {

  const handlePlaylistCardClick = (playlistId) => {
    onLoadPlaylist(playlistId);
  };

  const handleTrackClick = (e, playlistId, trackId) => {
    e.stopPropagation();
    onLoadPlaylistFromTrack(playlistId, trackId);
  };

  return (
    <div className="playlist-manager-section">
      <h3>Мои плейлисты</h3>
      <div className="playlist-grid">
        {(userPlaylists || []).map(playlist => (
          <div key={playlist.id} className="playlist-card" onClick={() => handlePlaylistCardClick(playlist.id)}>
            <div className="playlist-card-cover">
              <img src={playlist.last_track_cover_url || '/default-music-cover.png'} alt={playlist.name} />
            </div>
            <div className="playlist-card-content">
              <h4>{playlist.name} ({playlist.track_count})</h4>
              
              {playlist.preview_tracks && playlist.preview_tracks.length > 0 ? (
                <ul className="playlist-card-tracks-preview">
                  {playlist.preview_tracks.map(track => (
                    <li 
                      key={track.id} 
                      className="playlist-card-tracks-preview-item"
                      onClick={(e) => handleTrackClick(e, playlist.id, track.id)}
                    >
                      <span className="preview-item-title">{track.title}</span>
                      <span className="preview-item-artist">{track.artist}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="playlist-card-tracks">
                  <p>Плейлист пуст</p>
                </div>
              )}
            </div>
          </div>
        ))}
        <div className="playlist-card create-new-card" onClick={onTriggerCreateNewPlaylist}>
          <h4>+ Создать новый</h4>
        </div>
      </div>
    </div>
  );
}
