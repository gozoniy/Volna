// react/src/views/PlayerView.jsx
import React, { useState, useEffect, useRef } from 'react';
import ProgressBar from '../components/ProgressBar';
import TrackList from '../components/TrackList';
import PlaylistManager from '../components/PlaylistManager';
import AddTrackModal from '../components/AddTrackModal';

import { getAverageColor } from '../utils/colorExtractor';

function rgbToHsl(r, g, b) {
  r /= 255, g /= 255, b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h, s, l = (max + min) / 2;
  if (max === min) {
    h = s = 0; // achromatic
  } else {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
    }
    h /= 6;
  }
  return [h, s, l];
}

function hslToRgb(h, s, l) {
  let r, g, b;
  if (s === 0) {
    r = g = b = l; // achromatic
  } else {
    const hue2rgb = (p, q, t) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    };
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1/3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1/3);
  }
  return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}

function adjustColor(rgbColor, theme) {
    if (!rgbColor) return '#808080';
    const [h, s, l] = rgbToHsl(rgbColor[0], rgbColor[1], rgbColor[2]);

    let adjustedL = l;
    let adjustedS = s;

    if (theme === 'dark') {
        adjustedL = Math.min(0.82, l + 0.2);
        adjustedS = s * 0.85;
    } else { // Light theme
        adjustedL = Math.max(0.18, l - 0.2); // Make it darker for light theme shadow
        adjustedS = Math.min(1, s * 1.1); // Boost saturation slightly
    }

    const [r, g, b] = hslToRgb(h, adjustedS, adjustedL);
    const toHex = c => ('0' + c.toString(16)).slice(-2);
    return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

export default function PlayerView({
  API_URL,
  userId,
  currentTrack,
  currentPlaylist,
  isPlaying,
  isLoading,
  audioRef,
  onTogglePlay,
  onNext,
  onPrev,
  onFindWave,
  onPlaylistTrackSelect,
  onAddTrackToPlaylist,
  onCreatePlaylist,
  fetchPlaylists,
  userPlaylists,
  onColorChange,
  activeColor,
  theme,
  onLoadPlaylist,
  onLoadPlaylistFromTrack,
  currentPlaylistInfo,
  onCoverArtPositionChange
}) {
  const [showAddTrackModal, setShowAddTrackModal] = useState(false);
  const [createMode, setCreateMode] = useState(false);
  const [isLiked, setIsLiked] = useState(false);
  
  // Simplified state for cover art
  const [topArtSrc, setTopArtSrc] = useState(theme === 'dark' ? '/default-music-cover-dark.png' : '/default-music-cover.png');
  const [bottomArtSrc, setBottomArtSrc] = useState(null);

    const coverArtRef = useRef(null);

  

  

        const [topVisible, setTopVisible] = useState(false);

  

    

    useEffect(() => {
    const defaultCover = theme === 'dark' ? '/default-music-cover-dark.png' : '/default-music-cover.png';
    const newCover = currentTrack?.cover_url || defaultCover;

    if (newCover === topArtSrc) return;

    setTopArtSrc(newCover);
    setTopVisible(true);

    const animationDuration = 500; // Corresponds to the CSS transition duration
    setTimeout(() => {
      setBottomArtSrc(newCover);
    }, animationDuration);

    getAverageColor(newCover)
      .then(rgb => onColorChange(adjustColor(rgb, theme)))
      .catch(() => onColorChange(currentTrack?.color || '#808080'));
      
  }, [currentTrack, theme, onColorChange]);

  useEffect(() => {
    const updatePosition = () => {
      if (coverArtRef.current && onCoverArtPositionChange) {
        const rect = coverArtRef.current.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height;
        onCoverArtPositionChange({ x, y });
      }
    };
    updatePosition();
    window.addEventListener('resize', updatePosition);
    const timeout = setTimeout(updatePosition, 100);
    return () => {
      window.removeEventListener('resize', updatePosition);
      clearTimeout(timeout);
    }
  }, [currentTrack, onCoverArtPositionChange]);

  const triggerAddTrackModal = (mode = false) => {
    setCreateMode(mode);
    setShowAddTrackModal(true);
  };

  const handleLike = async () => {
    if (!currentTrack) return;

    setIsLiked(true);
    setTimeout(() => setIsLiked(false), 500); // Reset after animation

    let likedPlaylist = userPlaylists.find(p => p.name === 'Мне нравится');

    if (!likedPlaylist) {
      // If the "Liked" playlist doesn't exist, create it
      const newPlaylist = await onCreatePlaylist('Мне нравится');
      if (newPlaylist) {
        likedPlaylist = newPlaylist;
      } else {
        // Handle error in playlist creation
        console.error("Could not create 'Мне нравится' playlist.");
        return;
      }
    }

    onAddTrackToPlaylist(likedPlaylist.id, currentTrack.id);
  };
  const shadowOpacity = theme === 'dark' ? '50' : '80';



return (
  <div className="view-container player-view player-with-playlists-view">

    <div className="player-top-section">

      <div className="player-main-area">
        <div className="player-artwork" ref={coverArtRef} style={{ position: 'relative' }}>
  {/* Нижний слой с тенью */}
  {bottomArtSrc && (
    <img
      src={bottomArtSrc}
      alt=""
      className="artwork-image artwork-bottom"
      style={{
        boxShadow: `0 0 35px 5px ${activeColor}${shadowOpacity}`,
        width: '100%',
        height: '100%',
        position: 'absolute',
        top: 0,
        left: 0,
      }}

    />
  )}

  {/* Верхний слой для fade-in, без тени */}
  {topArtSrc && (
    <img
      src={topArtSrc}
      alt=""
      className={`artwork-image artwork-top ${topVisible ? 'visible' : ''}`}
      style={{
        width: '100%',
        height: '100%',
        position: 'absolute',
        top: 0,
        left: 0,
        transition: 'opacity 0.5s ease-in-out',
        opacity: topVisible ? 1 : 0,
      }}
    />
  )}
</div>
{/* 
        <div className="player-artwork">
          <img
            src={bottomArtSrc}
            alt=""
            className="artwork-image artwork-bottom"
            style={{ boxShadow: `0 0 35px 5px ${activeColor}50` }}
          />

          <img
            ref={coverArtRef}
            key={artKey}
            src={topArtSrc}
            alt=""
            className="artwork-image artwork-top"
            style={{ boxShadow: `0 0 35px 5px ${activeColor}50` }}
          />
        </div> */}

        <h2 className="player-track-title">
          {currentTrack?.artist} - {currentTrack?.title}
        </h2>

        <p className="player-artist-name">
          {currentTrack?.genre || "Неизвестный жанр"}
        </p>

        <ProgressBar audioRef={audioRef} />

        <div className="player-controls-wrapper">

          <button
            onClick={onFindWave}
            className="control-button wave"
            disabled={isLoading}
          >
            Волна
          </button>

          <div className="player-controls">
            <button
              onClick={onPrev}
              className="control-button secondary"
              disabled={isLoading}
            >
              <div className="icon-prev"></div>
            </button>

            <button
              onClick={onTogglePlay}
              className="control-button play-pause"
              disabled={isLoading}
              style={
                activeColor
                  ? { boxShadow: `0 0 15px 3px ${activeColor}80` }
                  : {}
              }
            >
              <div className={isPlaying ? "icon-pause" : "icon-play"}></div>
            </button>

            <button
              onClick={onNext}
              className="control-button secondary"
              disabled={isLoading}
            >
              <div className="icon-next"></div>
            </button>
          </div>

          <div className="player-controls-right">
            <button
              onClick={handleLike}
              className={`control-button like-button ${isLiked ? 'liked' : ''}`}
              disabled={!currentTrack || isLoading}
            >
              <svg viewBox="0 0 24 24">
                <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
              </svg>
            </button>
            <button
              onClick={() => triggerAddTrackModal(false)}
              className="control-button add-to-playlist"
              disabled={!currentTrack || isLoading}
            >
              +
            </button>
          </div>

        </div>
      </div>

      <div className="playlist-area">
        <div className="playlist-header">
          <h3>{currentPlaylistInfo.name}</h3>
        </div>

        <TrackList
          API_URL={API_URL}
          key={
            currentPlaylist.length > 0
              ? currentPlaylist.map((t) => t.id).join("-")
              : "empty"
          }
          tracks={currentPlaylist}
          currentTrack={currentTrack}
          onTrackSelect={onPlaylistTrackSelect}
        />
      </div>

    </div>

    <div className="playlists-manager-section">
      <PlaylistManager
        userId={userId}
        onPlaylistTrackSelect={onPlaylistTrackSelect}
        userPlaylists={userPlaylists}
        onCreatePlaylist={onCreatePlaylist}
        onTriggerCreateNewPlaylist={() => triggerAddTrackModal(true)}
        fetchPlaylists={fetchPlaylists}
        onLoadPlaylist={onLoadPlaylist}
        onLoadPlaylistFromTrack={onLoadPlaylistFromTrack}
      />
    </div>

    <AddTrackModal
      show={showAddTrackModal}
      onClose={() => setShowAddTrackModal(false)}
      currentTrackId={currentTrack?.id}
      userId={userId}
      playlists={userPlaylists}
      onAddConfirm={onAddTrackToPlaylist}
      onCreatePlaylist={onCreatePlaylist}
      fetchPlaylists={fetchPlaylists}
      createMode={createMode}
    />

  </div>
);

}