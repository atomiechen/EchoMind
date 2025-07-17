import { useState, useRef, useEffect, useCallback } from 'react';
import { Button, Select, Stack } from '@mantine/core';
import { IconMicrophoneFilled, IconMicrophoneOff } from '@tabler/icons-react';
import { socket } from '@/lib/socket';
import { useMeetingStore } from '@/store/meetingStore';
import { useTranslation } from "react-i18next";
import { AudioRecorder } from '@/lib/audiorecorder';


export const Recorder = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [clickRunning, setClickRunning] = useState(false);
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const audioRecorderRef = useRef<AudioRecorder>(null);
  const stepTimeRef = useRef<number | null>(null);
  const meetingId = useMeetingStore(s => s.meetingId);

  const { t } = useTranslation();

  const startRecording = () => {
    console.log("Start recording...");
    setClickRunning(true);

    const audioRecorder = new AudioRecorder((pcm: Int16Array) => {
      const current = Date.now();
      socket.emit('audioChunk', pcm, {
        meeting_id: meetingId,
        encodingType: 'pcm',
        begin: stepTimeRef.current!,
        end: current,
      });
      stepTimeRef.current = current;
    });
    audioRecorderRef.current = audioRecorder;
    audioRecorder.start().then(() => {
      const current = Date.now();
      stepTimeRef.current = current;
      socket.emit('toggleMic', {
        meeting_id: meetingId,
        enable: true,
        timestamp: current,
      });
      setIsRecording(true);
    }).finally(() => {
      setClickRunning(false);
    });
  };

  const stopRecording = useCallback(() => {
    console.log("Stop recording...");
    if (audioRecorderRef.current) {
      setClickRunning(true);
      audioRecorderRef.current.stop().then(() => {
        socket.emit('toggleMic', {
          meeting_id: meetingId,
          enable: false,
          timestamp: Date.now(),
        });
        setIsRecording(false);
      }).finally(() => {
        setClickRunning(false);
      });
      audioRecorderRef.current = null;
    }
  }, [meetingId]);

  useEffect(() => {
    // 监听设备的变化
    const handleDeviceChange = () => {
      navigator.mediaDevices.enumerateDevices().then((devices) => {
        const audioInputDevices = devices.filter((device) => device.kind === 'audioinput');
        setAudioDevices(audioInputDevices);
        if (audioInputDevices.length > 0 && !selectedDeviceId) {
          setSelectedDeviceId(audioInputDevices[0].deviceId); // 默认选择第一个设备
        }
      }).catch((error) => {
        console.error("Error enumerating devices:", error);
      });
    };

    // 初始获取设备列表
    handleDeviceChange();

    // 监听设备的连接和断开
    navigator.mediaDevices.addEventListener('devicechange', handleDeviceChange);
    
    // 请求音频权限
    const requestAudioPermission = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop()); // 立即停止流
        // 权限请求后，更新设备列表
        handleDeviceChange();
      } catch (error) {
        console.error("Error accessing media devices:", error);
      }
    };
    
    requestAudioPermission();

    return () => {
      navigator.mediaDevices.removeEventListener('devicechange', handleDeviceChange);
      // 关闭录制
      stopRecording();
    };
  }, [selectedDeviceId, stopRecording]);

  return (
    <Stack>
      <Select
        description={t('chooseMicrophone')}
        placeholder={t('chooseMicrophone')}
        value={selectedDeviceId}
        onChange={setSelectedDeviceId}
        data={audioDevices.map((device) => ({ value: device.deviceId, label: device.label }))} 
      />
      <Button 
        onClick={isRecording ? stopRecording : startRecording}
        variant={isRecording ? 'filled' : 'light'}
        color={isRecording ? 'orange' : 'gray'}
        disabled={clickRunning}
      >
        {isRecording ? <IconMicrophoneFilled /> : <IconMicrophoneOff />}
      </Button>
    </Stack>
  );
};
