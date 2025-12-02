// react/src/components/ProgressBar.jsx
import React, { useState, useEffect, useRef } from 'react';

export default function ProgressBar({ audioRef }) {
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const progressBarRef = useRef(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateProgress = () => {
      const currentProgress = (audio.currentTime / audio.duration) * 100;
      setProgress(isNaN(currentProgress) ? 0 : currentProgress);
      setCurrentTime(audio.currentTime);
    };
    const handleLoadedMetadata = () => setDuration(audio.duration);

    audio.addEventListener('timeupdate', updateProgress);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);

    return () => {
      audio.removeEventListener('timeupdate', updateProgress);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
    };
  }, [audioRef]);

  const handleProgressClick = (e) => {
    const audio = audioRef.current;
    const progressBar = progressBarRef.current;
    if (!audio || !progressBar || !duration) return;

    const rect = progressBar.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const progressBarWidth = rect.width;
    
    const newProgress = (clickX / progressBarWidth);
    const newTime = newProgress * duration;
    
    audio.currentTime = newTime;
  };

  const formatTime = (time) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60).toString().padStart(2, '0');
    return isNaN(minutes) || isNaN(seconds) ? '0:00' : `${minutes}:${seconds}`;
  };

  return (
    <div className="progress-bar-container">
      <span className="time-display">{formatTime(currentTime)}</span>
      
      {/* Кастомный прогресс-бар для анимации бегунка */}
      <div 
        className="custom-progress-track"
        ref={progressBarRef}
        onClick={handleProgressClick}
      >
        <div 
          className="custom-progress-filled"
          style={{ width: `${progress}%` }} 
        />
        <div 
          className="custom-progress-thumb"
          style={{ left: `${progress}%` }}
        />
      </div>

      <span className="time-display">{formatTime(duration)}</span>
    </div>
  );
}
