import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000';

export default function SettingsView() {
  const [scanProgress, setScanProgress] = useState({
    status: 'idle',
    total: 0,
    current: 0,
    filename: '',
  });
  const [isScanning, setIsScanning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [error, setError] = useState(null);

  const intervalRef = useRef(null);

  const fetchProgress = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/scan/progress`);
      const progress = response.data;
      setScanProgress(progress);

      if (progress.status === 'running') {
        setIsScanning(true);
        setIsPaused(false);
      } else if (progress.status === 'paused') {
        setIsScanning(true);
        setIsPaused(true);
      } else {
        setIsScanning(false);
        setIsPaused(false);
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    } catch (err) {
      console.error("Error fetching scan progress:", err);
      setError("Не удалось получить прогресс сканирования.");
      setIsScanning(false);
      setIsPaused(false);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  };

  const startScan = async () => {
    setError(null);
    try {
      await axios.post(`${API_URL}/api/scan/start`);
      setIsScanning(true);
      setIsPaused(false);
      if (!intervalRef.current) {
        intervalRef.current = setInterval(fetchProgress, 1000);
      }
    } catch (err) {
      console.error("Error starting scan:", err);
      setError(err.response?.data?.detail || "Не удалось запустить сканирование.");
    }
  };

  const handlePauseScan = async () => {
    try {
      await axios.post(`${API_URL}/api/scan/pause`);
      setIsPaused(true);
    } catch (err) {
      console.error("Error pausing scan:", err);
      setError(err.response?.data?.detail || "Не удалось приостановить сканирование.");
    }
  };

  const handleResumeScan = async () => {
    try {
      await axios.post(`${API_URL}/api/scan/resume`);
      setIsPaused(false);
    } catch (err) {
      console.error("Error resuming scan:", err);
      setError(err.response?.data?.detail || "Не удалось возобновить сканирование.");
    }
  };

  const handleClearLibrary = async () => {
    if (window.confirm('Вы уверены, что хотите очистить медиатеку? Это действие необратимо.')) {
      try {
        await axios.post(`${API_URL}/api/scan/clear`);
        // Optionally, reset progress view after clearing
        setScanProgress({ status: 'idle', total: 0, current: 0, filename: '' });
        alert('Медиатека успешно очищена.');
      } catch (err) {
        console.error("Error clearing library:", err);
        setError(err.response?.data?.detail || "Не удалось очистить медиатеку.");
      }
    }
  };

  const handleCancelScan = async () => {
    try {
      await axios.post(`${API_URL}/api/scan/cancel`);
      setIsScanning(false);
      setIsPaused(false);
      setScanProgress({ status: 'idle', total: 0, current: 0, filename: '' });
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    } catch (err) {
      console.error("Error cancelling scan:", err);
      setError(err.response?.data?.detail || "Не удалось отменить сканирование.");
    }
  };

  useEffect(() => {
    fetchProgress();
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const percentage = scanProgress.total > 0 ? (scanProgress.current / scanProgress.total) * 100 : 0;

  return (
    <div className="view-container settings-view">
      <h2>Настройки</h2>
      <div className="settings-section">
        <h3>Сканирование Медиатеки</h3>
        <p>Запустите сканирование, чтобы добавить новые треки в вашу медиатеку.</p>
        
        <div className="scan-controls">
          <button 
            onClick={startScan} 
            disabled={isScanning}
            className="scan-button"
          >
            {isScanning && !isPaused ? 'Сканирование...' : 'Запустить сканирование'}
          </button>

          <button 
            onClick={isPaused ? handleResumeScan : handlePauseScan}
            disabled={!isScanning}
            className="scan-button"
          >
            {isPaused ? 'Возобновить' : 'Пауза'}
          </button>
          
          <button 
            onClick={handleCancelScan}
            disabled={!isScanning}
            className="scan-button cancel-button"
          >
            Отменить
          </button>

          <button 
            onClick={handleClearLibrary}
            disabled={isScanning}
            className="scan-button clear-button"
          >
            Очистить
          </button>
        </div>

        {error && <p className="error-message">{error}</p>}

        {isScanning && (
          <div className="progress-container">
            <p>Статус: {scanProgress.status}</p>
            <p>Прогресс: {scanProgress.current} / {scanProgress.total}</p>
            <div className="progress-bar">
              <div 
                className="progress-bar-filled" 
                style={{ width: `${percentage}%` }}
              ></div>
            </div>
            <p className="current-file">Текущий файл: {scanProgress.filename}</p>
          </div>
        )}
      </div>
    </div>
  );
}
