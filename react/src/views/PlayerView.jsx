// react/src/views/PlayerView.jsx
import React, { useState, useEffect, useCallback } from 'react';
import jsmediatags from 'jsmediatags';
import { FastAverageColor } from 'fast-average-color';
import ProgressBar from '../components/ProgressBar';
import TrackList from '../components/TrackList';
import PlaylistManager from '../components/PlaylistManager';
import AddTrackModal from '../components/AddTrackModal';

const formatTrackName = (filename) => {
  if (!filename) return '';
  return filename.split('\\').pop();
};

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



    



    // Adjust lightness and saturation to "whiten" the color



    const adjustedL = Math.min(0.82, l + 0.2); // Add lightness, but cap it



    const adjustedS = s * 0.85; // Reduce saturation a bit







    const [r, g, b] = hslToRgb(h, adjustedS, adjustedL);



    



    // Convert to hex



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



  currentPlaylistInfo,



  onCoverArtPositionChange // New prop



}) {



      const [showAddTrackModal, setShowAddTrackModal] = useState(false);



      const [createMode, setCreateMode] = useState(false);



      const [coverArt, setCoverArt] = useState(theme === 'dark' ? '/default-music-cover-dark.png' : '/default-music-cover.png');



      const [previousCoverArt, setPreviousCoverArt] = useState(null);



      const [artKey, setArtKey] = useState(null);







      const coverArtRef = useRef(null); // Ref for the cover art image







      useEffect(() => {



        if (!currentTrack) {



          setCoverArt(theme === 'dark' ? '/default-music-cover-dark.png' : '/default-music-cover.png');



          onColorChange('#808080');



          return;



        }



    



        setPreviousCoverArt(coverArt);



    



        const trackUrl = `${API_URL}/audio/${currentTrack.filename.replace(/\\/g, '/')}`;



    



        jsmediatags.read(trackUrl, {



          onSuccess: (tag) => {



            const { picture } = tag.tags;



            if (picture) {



              let base64String = "";



              for (let i = 0; i < picture.data.length; i++) {



                base64String += String.fromCharCode(picture.data[i]);



              }



              const artUrl = `data:${picture.format};base64,${window.btoa(base64String)}`;



              setCoverArt(artUrl);



              setArtKey(currentTrack.id);



              fac.getColorAsync(artUrl, { 



                  algorithm: 'dominant',



                  ignoredColor: [0, 0, 0, 255, 255, 255, 255] 



                })



                 .then(color => {



                    const adjustedColor = adjustColor(color.value);



                    onColorChange(adjustedColor);



                 });



            } else {



              setCoverArt(theme === 'dark' ? '/default-music-cover-dark.png' : '/default-music-cover.png');



              setArtKey(currentTrack.id);



              onColorChange(currentTrack.color);



            }



          },



          onError: () => {



            setCoverArt(theme === 'dark' ? '/default-music-cover-dark.png' : '/default-music-cover.png');



            setArtKey(currentTrack.id);



            onColorChange(currentTrack.color);



          }



        });



      }, [currentTrack, theme]);







      // Effect to report cover art position



      useEffect(() => {



        const updatePosition = () => {



          if (coverArtRef.current && onCoverArtPositionChange) {



            const rect = coverArtRef.current.getBoundingClientRect();



            // Calculate center of the cover art for gradient origin



            const x = rect.left + rect.width / 2;



            const y = rect.top + rect.height; // Position under the cover art



            onCoverArtPositionChange({ x, y });



          }



        };







        // Update position initially and on window resize



        updatePosition();



        window.addEventListener('resize', updatePosition);



        // Also update if currentTrack changes, as it might re-render and affect position



        if (currentTrack) {



          // Give some time for rendering to settle, or use a MutationObserver



          const timeout = setTimeout(updatePosition, 100);



          return () => clearTimeout(timeout);



        }







        return () => window.removeEventListener('resize', updatePosition);



      }, [currentTrack, onCoverArtPositionChange]);







  const triggerAddTrackModal = (mode = false) => {



    setCreateMode(mode);



    setShowAddTrackModal(true);



  };







  return (



    <div className="view-container player-view player-with-playlists-view">



      <div className="player-top-section">



        <div className="player-main-area">



          <div className="player-artwork">



            <img src={previousCoverArt} alt="" className="artwork-image artwork-bottom" style={{ boxShadow: `0 0 35px 5px ${activeColor}50` }} />



            <img ref={coverArtRef} key={artKey} src={coverArt} alt="" className="artwork-image artwork-top" style={{ boxShadow: `0 0 35px 5px ${activeColor}50` }} />



          </div>







                              <h2 className="player-track-title">{currentTrack?.artist} - {currentTrack?.title}</h2>







                              <p className="player-artist-name">{currentTrack?.genre || 'Неизвестный жанр'}</p>



          



          <ProgressBar audioRef={audioRef} />







          <div className="player-controls-wrapper">



            <button onClick={onFindWave} className="control-button wave" disabled={isLoading}>Волна</button>



            <div className="player-controls">



              <button onClick={onPrev} className="control-button secondary" disabled={isLoading}><div className="icon-prev"></div></button>



              <button onClick={onTogglePlay} className="control-button play-pause" disabled={isLoading}><div className={isPlaying ? 'icon-pause' : 'icon-play'}></div></button>



              <button onClick={onNext} className="control-button secondary" disabled={isLoading}><div className="icon-next"></div></button>



              



              



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







                    key={currentPlaylist.length > 0 ? currentPlaylist.map(t => t.id).join('-') : 'empty'}







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



                  onLoadPlaylist={onLoadPlaylist} // Pass the new prop



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
