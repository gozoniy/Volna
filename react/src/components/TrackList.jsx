// react/src/components/TrackList.jsx
import React, { useRef, useEffect, useState } from 'react';

const formatTrackName = (filename) => {
  if (!filename) return '';
  return filename.split(/[/\\]/).pop();
};

const isColorDark = (color) => {
  if (!color) return false;
  let r, g, b;
  if (color.startsWith('#')) {
    const hex = color.substring(1);
    r = parseInt(hex.substring(0, 2), 16);
    g = parseInt(hex.substring(2, 4), 16);
    b = parseInt(hex.substring(4, 6), 16);
  } else if (color.startsWith('rgb')) {
    const rgb = color.match(/\d+/g);
    r = parseInt(rgb[0]);
    g = parseInt(rgb[1]);
    b = parseInt(rgb[2]);
  } else {
    return false;
  }
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance < 0.5;
};

export default function TrackList({ tracks, currentTrack, onTrackSelect, showLastPlayed = false }) {
  const listRef = useRef(null);
  const highlightRef = useRef(null);
  const itemRefs = useRef(new Map());
  const [isHighlightDark, setIsHighlightDark] = useState(false);
  const [playlistVersion, setPlaylistVersion] = useState(0);

  useEffect(() => {
    // Increment version whenever the track list changes to re-trigger animations
    setPlaylistVersion(v => v + 1);
  }, [tracks]);

  useEffect(() => {
    if (currentTrack) {
      setIsHighlightDark(isColorDark(currentTrack.color));
    }
  }, [currentTrack]);

  useEffect(() => {
    if (!currentTrack) {
      if (highlightRef.current) highlightRef.current.style.opacity = '0';
      return;
    }

    const targetNode = itemRefs.current.get(currentTrack.id);

    if (targetNode && highlightRef.current && listRef.current) {
      const { offsetTop, offsetHeight } = targetNode;
      highlightRef.current.style.transform = `translateY(${offsetTop}px)`;
      highlightRef.current.style.height = `${offsetHeight}px`;
      highlightRef.current.style.opacity = '1';

      const scrollTo = offsetTop - listRef.current.clientHeight / 2 + offsetHeight / 2;
      listRef.current.scrollTo({
        top: scrollTo,
        behavior: 'smooth',
      });
    } else {
      if (highlightRef.current) highlightRef.current.style.opacity = '0';
    }
  }, [currentTrack, tracks]);

  return (
    <div
      className="track-list-container"
      ref={listRef}
    >
      <div className="list-highlight" ref={highlightRef}></div>

      <ul className="track-list" key={playlistVersion}>
        {tracks.map((track, index) => {
          const isActive = currentTrack && track.id === currentTrack.id;
          const itemClasses = `track-item ${isActive ? 'active' : ''} ${isActive && isHighlightDark ? 'text-light' : ''}`;
          
          const activeIndex = currentTrack ? tracks.findIndex(t => t.id === currentTrack.id) : -1;
          const animationOrder = activeIndex !== -1 ? Math.abs(index - activeIndex) : index;

          return (
            <li
              key={track.id}
              ref={(node) => {
                if (node) {
                  itemRefs.current.set(track.id, node);
                } else {
                  itemRefs.current.delete(track.id);
                }
              }}
              className={itemClasses}
              onClick={() => onTrackSelect(track)}
              style={{ '--animation-order': animationOrder }}
            >
              <span className="track-color-dot" style={{ backgroundColor: track.color }}></span>

              <div className="track-item-info">
                <span className="track-item-name">{formatTrackName(track.filename)}</span>

                {showLastPlayed && track.last_played && (
                  <span className="track-item-last-played">
                    Слушали: {new Date(track.last_played * 1000).toLocaleString()}
                  </span>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
