import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import './App.css';

import BottomNav from './layout/BottomNav';
import PlayerView from './views/PlayerView';
import AllSongsView from './views/AllSongsView';

const API_URL = 'http://127.0.0.1:8000';

function getUserId() {
  let userId = localStorage.getItem('user_id');
  if (!userId) {
    userId = crypto.randomUUID();
    localStorage.setItem('user_id', userId);
  }
  return userId;
}

function App() {
  const [userId, setUserId] = useState(null);
  const [allTracks, setAllTracks] = useState([]);
  const [currentPlaylist, setCurrentPlaylist] = useState([]);
  const [currentTrack, setCurrentTrack] = useState(null); 
  const [currentTrackIndex, setCurrentTrackIndex] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [activeView, setActiveView] = useState('player'); 
  const [userPlaylists, setUserPlaylists] = useState([]);
  const [currentPlaylistInfo, setCurrentPlaylistInfo] = useState({ name: 'Текущий плейлист', isWave: false });

  const [isFading, setIsFading] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [showThemeTransition, setShowThemeTransition] = useState(false);
  const [mouseCoords, setMouseCoords] = useState({ x: 0, y: 0 });
  const [activeColor, setActiveColor] = useState(null);

  const audioRef = useRef(null);
  const gradientTimeoutRef = useRef(null);
  const themeButtonRef = useRef(null);

  useEffect(() => {
    document.documentElement.className = theme === 'light' ? 'light-theme' : '';
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    if (themeButtonRef.current) {
      const rect = themeButtonRef.current.getBoundingClientRect();
      const x = rect.left + rect.width / 2;
      const y = rect.top + rect.height / 2;
      setMouseCoords({ x, y });
    }
    
    setShowThemeTransition(true);
    setTimeout(() => {
      setTheme(prevTheme => {
        const newTheme = prevTheme === 'light' ? 'dark' : 'light';
        localStorage.setItem('theme', newTheme);
        return newTheme;
      });
    }, 300);
    setTimeout(() => {
      setShowThemeTransition(false);
    }, 1000);
  }, []);

  const fetchPlaylists = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/playlists`);
      setUserPlaylists(response.data);
    } catch (error) {
      console.error("Ошибка загрузки плейлистов:", error);
    }
  }, []);

  useEffect(() => {
    const loadInitialData = async () => {
      const id = getUserId();
      setUserId(id);
  
      try {
        // 1. Получаем последний проигранный трек
        const lastPlayedRes = await axios.get(`${API_URL}/api/history/last`, { 
          params: { user_id: id }
        }).catch(() => null);
  
        let lastPlayedTrack = null;
        if (lastPlayedRes?.data) {
          lastPlayedTrack = lastPlayedRes.data;
          // Устанавливаем его сразу, чтобы пользователь что-то увидел
          setCurrentTrack(lastPlayedTrack);
          setActiveColor(lastPlayedTrack.color);
          setCurrentPlaylist([lastPlayedTrack]);
          setCurrentTrackIndex(0);
          if (audioRef.current) {
            audioRef.current.src = `${API_URL}/audio/${lastPlayedTrack.filename.replace(/\\/g, '/')}`;
          }
        }
  
        // 2. Параллельно получаем все ID треков и плейлисты
        await Promise.all([
          (async () => {
            const tracksIdsRes = await axios.get(`${API_URL}/api/tracks`).catch(() => null);
            if (tracksIdsRes?.data) {
              // 3. Получаем детали для всех треков в фоне
              const allTrackDetails = await axios.post(`${API_URL}/api/tracks_by_ids`, {
                track_ids: tracksIdsRes.data,
                user_id: id
              }).catch(() => null);

              if (allTrackDetails?.data) {
                setAllTracks(allTrackDetails.data);
              }
            }
          })(),
          fetchPlaylists()
        ]);
  
      } catch (error) {
        console.error("Ошибка при начальной загрузке данных:", error);
      }
    };
  
    loadInitialData();
  }, [fetchPlaylists]);
  
  useEffect(() => {
    const root = document.documentElement;
    if (gradientTimeoutRef.current) clearTimeout(gradientTimeoutRef.current);
    
    if (activeColor) {
      setIsFading(true);
      gradientTimeoutRef.current = setTimeout(() => {
        root.style.setProperty('--primary-color', activeColor);
        setIsFading(false);
      }, 400);
    }
    return () => { if (gradientTimeoutRef.current) clearTimeout(gradientTimeoutRef.current); };
  }, [activeColor]);

  const handleColorChange = useCallback((newColor) => {
    setActiveColor(newColor);
    setCurrentTrack(prevTrack => {
      if (prevTrack && prevTrack.color !== newColor) {
        return { ...prevTrack, color: newColor };
      }
      return prevTrack;
    });
  }, []);

  const simplifiedPlayTrack = (filename, trackId) => { if (audioRef.current) { const audioSrc = `${API_URL}/audio/${filename.replace(/\\/g, '/')}`; if (audioRef.current.src !== audioSrc) { audioRef.current.src = audioSrc; if (trackId && userId) { axios.post(`${API_URL}/api/history/update`, { track_id: trackId, user_id: userId }).catch(e => console.error("Ошибка истории", e)); } } const p = audioRef.current.play(); if (p) { p.then(() => setIsPlaying(true)).catch(() => setIsPlaying(false)); } } };
  const simplifiedHandleSelect = (track) => { if (track && track.filename && !isLoading) { setCurrentTrack(track); setCurrentPlaylist([track]); setCurrentTrackIndex(0); simplifiedPlayTrack(track.filename, track.id); setActiveView('player'); } };
  const simplifiedFindWave = () => {
    if (currentTrack) {
      setIsLoading(true);
      axios.get(`${API_URL}/api/similar/${currentTrack.id}`, { params: { user_id: userId } })
        .then(res => {
          const newTracks = res.data.map(t => ({
            id: t.id,
            filename: t.filename,
            title: t.title || 'Неизвестный трек',
            artist: t.artist || 'Неизвестный исполнитель',
            genre: t.genre || 'Unknown',
            color: t.color || '#808080',
            last_played: t.last_played
          }));
          const p = [currentTrack, ...newTracks];
          setCurrentPlaylist(p);
                    const i = p.findIndex(t => t.filename === currentTrack.filename);
                    setCurrentTrackIndex(i >= 0 ? i : 0);
                    setCurrentPlaylistInfo({ name: `Волна по треку: ${currentTrack.title}`, isWave: true });
                  })
                  .catch(e => console.error("Ошибка 'волны'", e))
                  .finally(() => setIsLoading(false));
              }
            };
            
            const simplifiedTogglePlayPause = () => { if (currentTrack) { isPlaying ? audioRef.current.pause() : audioRef.current.play(); setIsPlaying(!isPlaying); } };
            const simplifiedPlayNext = () => { if (currentPlaylist.length > 0) { const i = (currentTrackIndex + 1) % currentPlaylist.length; const t = currentPlaylist[i]; setCurrentTrack(t); setCurrentTrackIndex(i); simplifiedPlayTrack(t.filename, t.id); } };
            const simplifiedPlayPrev = () => { if (currentPlaylist.length > 0) { const i = (currentTrackIndex - 1 + currentPlaylist.length) % currentPlaylist.length; const t = currentPlaylist[i]; setCurrentTrack(t); setCurrentTrackIndex(i); simplifiedPlayTrack(t.filename, t.id); } };
          
            const handleLoadPlaylist = useCallback(async (playlistId) => {
              setIsLoading(true);
              try {
                const response = await axios.get(`${API_URL}/api/playlists/${playlistId}/tracks`, {
                  params: { user_id: userId }
                });
                const { name, tracks } = response.data; // Destructure name and tracks
                if (tracks.length > 0) {
                  setCurrentPlaylist(tracks);
                  setCurrentTrack(tracks[0]);
                  setCurrentTrackIndex(0);
                  simplifiedPlayTrack(tracks[0].filename, tracks[0].id);
                } else {
                  setCurrentPlaylist([]);
                  setCurrentTrack(null);
                  setCurrentTrackIndex(-1);
                }
                setCurrentPlaylistInfo({ name: name, isWave: false }); // Update playlist info
                setActiveView('player'); // Switch to player view when a playlist is loaded
              } catch (error) {
                console.error("Ошибка загрузки плейлиста:", error);
                alert(error.response?.data?.detail || "Ошибка загрузки плейлиста");
              } finally {
                setIsLoading(false);
              }
            }, [userId, simplifiedPlayTrack]);
          
            const handleAddTrackToPlaylist = useCallback(async (playlistId, trackId) => {
              if (!userId || !trackId || !playlistId) return;
              try {
                await axios.post(`${API_URL}/api/playlists/add_track`, { user_id: userId, playlist_id: playlistId, track_id: trackId });
                fetchPlaylists(); 
                return true;
              } catch (error) {
                console.error("Ошибка добавления трека в плейлист:", error);
                alert(error.response?.data?.detail || "Ошибка добавления трека в плейлиста");
                return false;
              }
            }, [userId, fetchPlaylists]);
          
                const handleCreatePlaylist = useCallback(async (playlistName) => {
                  if (!userId || !playlistName.trim()) return null;
                  try {
                    const response = await axios.post(`${API_URL}/api/playlists/create`, { user_id: userId, name: playlistName });
                    fetchPlaylists();
                    return response.data.id;
                  } catch (error){
                    console.error("Ошибка создания плейлиста:", error);
                    alert(error.response?.data?.detail || "Ошибка создания плейлиста");
                    return null;
                  }
                }, [userId, fetchPlaylists]);
              
                const renderView = () => {
                  switch (activeView) {
                    case 'all-songs':
                      return <AllSongsView allTracks={allTracks} onTrackSelect={simplifiedHandleSelect} currentTrack={currentTrack} />;
                    default:
                      return (
                        <PlayerView
                          API_URL={API_URL}
                          userId={userId}
                          currentTrack={currentTrack} currentPlaylist={currentPlaylist}
                          isPlaying={isPlaying} isLoading={isLoading} audioRef={audioRef}
                          onTogglePlay={simplifiedTogglePlayPause} onNext={simplifiedPlayNext} onPrev={simplifiedPlayPrev}
                          onFindWave={simplifiedFindWave}
                          onLoadPlaylist={handleLoadPlaylist} // Pass the new handler
                          currentPlaylistInfo={currentPlaylistInfo} // Pass playlist info
                          onPlaylistTrackSelect={(track) => {
                            const index = currentPlaylist.findIndex(t => t.filename === track.filename);
                            if (index > -1) { setCurrentTrack(currentPlaylist[index]); setCurrentTrackIndex(index); simplifiedPlayTrack(track.filename, track.id); }
                          }}
                          userPlaylists={userPlaylists}
                          onAddTrackToPlaylist={handleAddTrackToPlaylist}
                          onCreatePlaylist={handleCreatePlaylist}
                          fetchPlaylists={fetchPlaylists}
                          tracks={currentPlaylist}
                          onColorChange={handleColorChange}
                          activeColor={activeColor}
                          theme={theme}
                        />
                      );
                  }
                };  return (
    <div className={`App ${currentTrack ? 'track-active' : ''} ${isFading ? 'gradient-fading' : ''}`}>
      <div 
        className={`theme-transition-overlay ${showThemeTransition ? 'active' : ''}`}
        style={{
          '--mouse-x': `${mouseCoords.x}px`,
          '--mouse-y': `${mouseCoords.y}px`,
          '--gradient-color-start': theme === 'dark' ? 'rgba(36, 36, 36, 1)' : 'rgba(255, 255, 255, 1)',
          '--gradient-color-end': theme === 'dark' ? 'rgba(36, 36, 36, 0.7)' : 'rgba(255, 255, 255, 0.7)'
        }}
      ></div>

      <div className="app-header">
        <div className="profile-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
        </div>
        <button ref={themeButtonRef} onClick={toggleTheme} className="theme-toggle-button">
          {theme === 'dark' ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"></path></svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path><path d="M4.93 4.93l1.41 1.41"></path><path d="M17.66 17.66l1.41 1.41"></path><path d="M2 12h2"></path><path d="M20 12h2"></path><path d="M4.93 19.07l1.41-1.41"></path><path d="M17.66 6.34l1.41-1.41"></path></svg>
          )}
        </button>
      </div>

      <main className="main-view">{renderView()}</main>
      <BottomNav activeView={activeView} setActiveView={setActiveView} />
      <audio ref={audioRef} onEnded={simplifiedPlayNext} />
    </div>
  );
}

export default App;
