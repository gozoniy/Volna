// react/src/views/AllSongsView.jsx
import React, { useState, useMemo } from 'react';
import TrackList from '../components/TrackList'; // Импортируем новый компонент

export default function AllSongsView({ API_URL, allTracks, onTrackSelect, currentTrack }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('default');

  const formatTrackName = (filename) => filename.split('\\').pop();

  const sortedAndFilteredTracks = useMemo(() => {
    let processedTracks = [...allTracks];
    if (sortBy === 'name') {
      processedTracks.sort((a, b) => formatTrackName(a.filename).localeCompare(formatTrackName(b.filename)));
    } else if (sortBy === 'date') {
      processedTracks.sort((a, b) => (b.last_played || 0) - (a.last_played || 0));
    }
    if (searchTerm) {
      const lowercasedFilter = searchTerm.toLowerCase();
      processedTracks = processedTracks.filter(track =>
        formatTrackName(track.filename).toLowerCase().includes(lowercasedFilter)
      );
    }
    return processedTracks;
  }, [allTracks, searchTerm, sortBy]);

  return (
    <div className="view-container all-songs-view">
      <div className="view-header">
        <h1>Все песни</h1>
        <div className="search-container">
          <input
            type="text"
            placeholder="Поиск по всей медиатеке..."
            className="search-input"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="sort-controls">
          <span>Сортировать:</span>
          <button className={sortBy === 'default' ? 'active' : ''} onClick={() => setSortBy('default')}>По умолчанию</button>
          <button className={sortBy === 'name' ? 'active' : ''} onClick={() => setSortBy('name')}>По имени</button>
          <button className={sortBy === 'date' ? 'active' : ''} onClick={() => setSortBy('date')}>По дате</button>
        </div>
      </div>
      
      {/* Используем новый компонент TrackList */}
      <TrackList
        API_URL={API_URL}
        tracks={sortedAndFilteredTracks}
        currentTrack={currentTrack}
        onTrackSelect={onTrackSelect}
        showLastPlayed={true} // Показываем дату прослушивания в этом списке
      />
    </div>
  );
}
