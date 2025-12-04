// react/src/views/PlayerView.jsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { FastAverageColor } from 'fast-average-color';
import ProgressBar from '../components/ProgressBar';
import TrackList from '../components/TrackList';
import PlaylistManager from '../components/PlaylistManager';
import AddTrackModal from '../components/AddTrackModal';

const fac = new FastAverageColor();

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

function adjustColor(rgbColor) {
    if (!rgbColor) return '#808080';
    const [h, s, l] = rgbToHsl(rgbColor[0], rgbColor[1], rgbColor[2]);
    const adjustedL = Math.min(0.82, l + 0.2);
    const adjustedS = s * 0.85;
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
  
  // Simplified state for cover art
  const [topArtSrc, setTopArtSrc] = useState(theme === 'dark' ? '/default-music-cover-dark.png' : '/default-music-cover.png');
  const [bottomArtSrc, setBottomArtSrc] = useState(null);
  const [artKey, setArtKey] = useState(0);

  const coverArtRef = useRef(null);


  const [topVisible, setTopVisible] = useState(false);

  useEffect(() => {
      const defaultCover = theme === 'dark'
          ? '/default-music-cover-dark.png'
          : '/default-music-cover.png';
      const newCover = currentTrack?.cover_url || defaultCover;

      // 1. Сначала скрываем верхнюю обложку
      setTopVisible(false);

      // 2. Через маленький timeout меняем src и делаем fade-in
      setTimeout(() => {
          setTopArtSrc(newCover);
          setTopVisible(true);
      }, 50); // 50ms достаточно, чтобы браузер отрендерил opacity=0

      // 3. Обновляем нижнюю обложку после завершения анимации
      setTimeout(() => {
          setBottomArtSrc(newCover);
      }, 2000);

      fac.getColorAsync(newCover, { algorithm: 'dominant', ignoredColor: [0,0,0,255,255,255,255] })
          .then(color => onColorChange(adjustColor(color.value)))
          .catch(() => onColorChange(currentTrack?.color || '#808080'));
  }, [currentTrack, theme, onColorChange]);

  useEffect(() => {
    const defaultCover = theme === 'dark' ? '/default-music-cover-dark.png' : '/default-music-cover.png';
    const newCover = currentTrack?.cover_url || defaultCover;

    if (newCover === bottomArtSrc) return; // если та же обложка, ничего не делаем

    // ставим новый src на верхний слой, скрытый
    setTopArtSrc(newCover);
    setTopVisible(false);
  }, [currentTrack, theme]);

  // Когда верхний слой загружен, запускаем fade-in
  const handleTopLoad = () => {
    setTopVisible(true);
    // через время анимации обновляем нижний слой
    setTimeout(() => {
      setBottomArtSrc(topArtSrc);
      setTopArtSrc(null); // очищаем верхний слой
      setTopVisible(false);
    }, 2000); // совпадает с transition-duration в CSS
  };

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
        boxShadow: `0 0 35px 5px ${activeColor}50`,
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
      onLoad={handleTopLoad}
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

          <button
            onClick={() => triggerAddTrackModal(false)}
            className="control-button add-to-playlist"
            disabled={!currentTrack || isLoading}
          >
            +
          </button>

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