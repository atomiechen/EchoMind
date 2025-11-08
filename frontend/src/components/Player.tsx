import { useRef, useState, useEffect, forwardRef, useImperativeHandle } from 'react';
import { Slider, Button, Select, Text } from '@mantine/core';
import { IconPlayerPlay, IconPlayerPause, IconVolume, IconDownload } from '@tabler/icons-react';
import { useMeetingStore } from '@/store/meetingStore';
import { API_BASE_URL } from '@/lib/constants';
import { error } from '@/lib/notifications';
import { useTranslation } from 'react-i18next';


const formatTime = (seconds: number) => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  return `${hours > 0 ? `${hours}:` : ''}${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
};

export type PlayerHandle = {
  setCurrentTime: (time: number) => void;
};

export const Player = forwardRef<PlayerHandle>((props, ref) => {
  const meetingId = useMeetingStore(s => s.meetingId);
  const { t } = useTranslation();

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioCurrentTime, setAudioCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(1);

  const audioUrl = `${API_BASE_URL}/audio/${meetingId}`;

  // 只在audioUrl变化时更新audioRef的src
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.src = audioUrl;
      audioRef.current.load();
      console.log("Loading audio from URL:", audioUrl);
    }
  }, [audioUrl]);

  useImperativeHandle(ref, () => ({
    setCurrentTime: (time: number) => {
      if (audioRef.current) {
        audioRef.current.currentTime = time;
        setAudioCurrentTime(time); // 更新当前时间
        console.log("useImperativeHandle", time, audioRef.current.currentTime);
      }
    },
  }));

  useEffect(() => {
    const current = audioRef.current;
    if (current) {
      current.addEventListener('timeupdate', updateCurrentTime);
      current.addEventListener('loadedmetadata', updateDuration);
    }

    return () => {
      if (current) {
        current.removeEventListener('timeupdate', updateCurrentTime);
        current.removeEventListener('loadedmetadata', updateDuration);
      }
    };
  }, [audioUrl]);

  const updateCurrentTime = () => {
    if (audioRef.current) {
      setAudioCurrentTime(audioRef.current.currentTime);
      console.log("updateCurrentTime", audioRef.current.currentTime);
    }
  };

  const updateDuration = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
      console.log("Audio duration:", audioRef.current.duration); // 打印时长，确认是否加载
    }
  };

  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play().catch((err) => {
          error(t('audioNotFound'), t('audioNotFoundMessage'));
        });
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleSliderChange = (value: number) => {
    if (audioRef.current) {
      const numericValue = Number(value); // 确保是数字
      if (!isNaN(numericValue) && numericValue >= 0 && numericValue <= audioRef.current.duration) {
        audioRef.current.currentTime = numericValue;
        setAudioCurrentTime(numericValue);
        console.log("Slider value:", numericValue, audioRef.current.currentTime);
      }
    }
  };

  const handleSliderChangeEnd = (value: number) => {
    if (audioRef.current) {
      const numericValue = Number(value); // 确保是数字
      if (!isNaN(numericValue) && numericValue >= 0 && numericValue <= audioRef.current.duration) {
        audioRef.current.currentTime = numericValue;
        setAudioCurrentTime(numericValue);
        console.log("Slider end:", numericValue, audioRef.current.currentTime);
      }
    }
  };

  const handleVolumeChange = (value: number) => {
    if (audioRef.current) {
      audioRef.current.volume = value;
      setVolume(value);
    }
  };

  const handlePlaybackRateChange = (value: string | null) => {
    if (audioRef.current && value) {
      audioRef.current.playbackRate = parseFloat(value);
      setPlaybackRate(parseFloat(value));
    }
  };

  const handleDownload = () => {
    // downloadMeetingFile(meetingId);
  };

  return (
    <div style={{ padding: '20px', borderRadius: '8px', backgroundColor: '#f9f9f9', boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)' }}>
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          onLoadedMetadata={updateDuration}
          onEnded={() => setIsPlaying(false)}
          // onError={(e) => console.error('Audio error:', e)}
        />
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <Slider
          value={audioCurrentTime}
          label={(value) => `${formatTime(value)}`}
          onChange={handleSliderChange}
          onChangeEnd={handleSliderChangeEnd}
          max={duration}
          style={{ flex: 1, marginRight: '10px' }}
        />
        <Text size='sm'>{`${formatTime(audioCurrentTime)} / ${formatTime(duration)}`}</Text>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <Button onClick={togglePlay} variant="light" size="xs">
          {isPlaying ? <IconPlayerPause size={16} /> : <IconPlayerPlay size={16} />}
        </Button>

        <Select
          checkIconPosition='right'
          value={playbackRate.toString()}
          onChange={handlePlaybackRateChange}
          data={[
            { value: '0.5', label: '0.5x' },
            { value: '1', label: '1x' },
            { value: '1.5', label: '1.5x' },
            { value: '2', label: '2x' },
            { value: '3', label: '3x' },
          ]}
          style={{ width: '80px' }}
          size="xs"
        />

        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <IconVolume size={16} />
          <Slider
            value={volume}
            onChange={handleVolumeChange}
            max={1}
            step={0.01}
            style={{ width: '80px' }}
            label={(value) => `${Math.round(value * 100)}`}
          />
        </div>

        <Button onClick={handleDownload} variant="light" size="xs">
          <IconDownload size={16} />
        </Button>
      </div>
    </div>
  );
});
