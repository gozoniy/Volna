// react/src/views/AllSongsView.jsx
import React, { useState, useEffect, useCallback } from 'react';
import InfiniteScroll from 'react-infinite-scroll-component';
import TrackList from '../components/TrackList';
import axios from 'axios';

export default function AllSongsView({ API_URL, onTrackSelect, currentTrack, userId }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('date');
  const [tracks, setTracks] = useState([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  const fetchTracks = useCallback(async (isSearch = false, newPage = 1) => {
    setIsLoading(true);
    try {
      let response;
      if (isSearch) {
        response = await axios.get(`${API_URL}/api/tracks/search`, { params: { q: searchTerm, user_id: userId } });
        setTracks(response.data);
        setHasMore(false);
      } else {
        response = await axios.get(`${API_URL}/api/history/all`, { params: { user_id: userId, page: newPage, page_size: 50 } });
        setTracks(prevTracks => newPage === 1 ? response.data : [...prevTracks, ...response.data]);
        setHasMore(response.data.length > 0);
      }
      setPage(newPage + 1);
    } catch (error) {
      console.error("Error fetching tracks:", error);
    } finally {
      setIsLoading(false);
    }
  }, [API_URL, userId, searchTerm]);

  useEffect(() => {
    if (searchTerm) {
      const handler = setTimeout(() => {
        setPage(1);
        setTracks([]);
        fetchTracks(true, 1);
      }, 500); // Debounce search
      return () => clearTimeout(handler);
    } else {
      setPage(1);
      setTracks([]);
      fetchTracks(false, 1);
    }
  }, [searchTerm, fetchTracks]);

  const fetchMoreData = () => {
    if (!isLoading && hasMore) {
      fetchTracks(false, page);
    }
  };

  // The 'sortedAndFilteredTracks' logic is now handled by the backend.
  // The 'sortBy' state is not used for now, but can be used later to pass sorting params to the API.

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
      
      <InfiniteScroll
        dataLength={tracks.length}
        next={fetchMoreData}
        hasMore={hasMore && !searchTerm}
        // loader={<h4>Loading...</h4>}
        // endMessage={<p style={{ textAlign: 'center' }}><b>Yay! You have seen it all</b></p>}
        scrollableTarget="main-view" // Assuming main-view is the scrollable parent
      >
        <TrackList
          API_URL={API_URL}
          tracks={tracks}
          currentTrack={currentTrack}
          onTrackSelect={onTrackSelect}
          showLastPlayed={true}
        />
      </InfiniteScroll>
    </div>
  );
}
