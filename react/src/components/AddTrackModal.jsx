// react/src/components/AddTrackModal.jsx
import React, { useState, useEffect} from 'react';
import axios from 'axios'; // axios здесь нужен для onCreatePlaylist

const API_URL = 'http://127.0.0.1:8000'; // Добавляем API_URL

export default function AddTrackModal({ show, onClose, currentTrackId, userId, playlists, onAddConfirm, onCreatePlaylist, fetchPlaylists, createMode: initialCreateMode }) {
  const [newPlaylistName, setNewPlaylistName] = useState('');
  const [currentMode, setCurrentMode] = useState(initialCreateMode || false); // Инициализируем из пропсов

  // Обновляем currentMode, если initialCreateMode меняется извне
  useEffect(() => {
    setCurrentMode(initialCreateMode || false);
  }, [initialCreateMode]);

  if (!show || !currentTrackId || !userId) return null;

  // Функция для создания плейлиста, вызываемая из модального окна
  const handleCreateNewPlaylist = async () => {
    if (!newPlaylistName.trim()) return;
    try {
      const newPlaylistId = await onCreatePlaylist(newPlaylistName); // Вызываем колбэк из PlayerView/App
      if (newPlaylistId) {
        // Если успешно создан, сразу пытаемся добавить в него трек
        await onAddConfirm(newPlaylistId, currentTrackId); // Вызываем колбэк из PlayerView/App
        onClose(); // Закрываем модальное окно после добавления
      }
    } catch (error) {
      console.error("Ошибка создания плейлиста или добавления трека:", error);
      alert(error.response?.data?.detail || "Ошибка создания плейлиста или добавления трека");
    }
  };

  // Функция для добавления трека в существующий плейлист
  const handleAddTrackToExisting = async (playlistId) => {
    try {
      await onAddConfirm(playlistId, currentTrackId); // Вызываем колбэк из PlayerView/App
      onClose(); // Закрываем модальное окно после добавления
    } catch (error) {
      console.error("Ошибка добавления трека:", error);
      alert(error.response?.data?.detail || "Ошибка добавления трека в плейлист");
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h4>{currentMode ? 'Создать новый плейлист' : 'Добавить трек в плейлист'}</h4>
        
        {currentMode ? (
          <div className="create-playlist-form">
            <input
              type="text"
              placeholder="Название плейлиста"
              value={newPlaylistName}
              onChange={e => setNewPlaylistName(e.target.value)}
            />
            <div className="modal-actions">
              <button onClick={handleCreateNewPlaylist}>Создать и добавить</button>
              <button onClick={() => setCurrentMode(false)}>Назад</button>
            </div>
          </div>
        ) : (
          <>
            <div className="playlist-selection">
              {(playlists || []).map(playlist => (
                <button key={playlist.id} onClick={() => handleAddTrackToExisting(playlist.id)}>
                  {playlist.name}
                </button>
              ))}
            </div>
            <p className="create-new-text" onClick={() => setCurrentMode(true)}>
              Создать новый плейлист
            </p>
            <div className="modal-actions">
                <button onClick={onClose}>Отмена</button>
            </div>
          </>
        )}
        <button className="close-button" onClick={onClose}>✖</button>
      </div>
    </div>
  );
}