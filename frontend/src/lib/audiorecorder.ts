export class AudioRecorder {
  private context?: AudioContext;
  private processor?: ScriptProcessorNode;
  private source?: MediaStreamAudioSourceNode;
  private stream?: MediaStream;
  private onAudio;

  constructor(onAudio: (pcm: Int16Array) => void) {
    this.onAudio = onAudio;
  }

  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.context = new AudioContext({ sampleRate: 16000 });
    this.source = this.context.createMediaStreamSource(this.stream);
    this.processor = this.context.createScriptProcessor(4096 * 4, 1, 1);  // 调大 bufferSize 可以减少回调频率
    this.processor.onaudioprocess = (e) => {
      const float32 = e.inputBuffer.getChannelData(0);
      const pcm = new Int16Array(float32.length);
      for (let i = 0; i < float32.length; i++) {
        pcm[i] = Math.max(-1, Math.min(1, float32[i]!)) * 32767;
      }
      this.onAudio(pcm);
    };
    this.source.connect(this.processor);
    this.processor.connect(this.context.destination);
  }

  async stop() {
    this.processor?.disconnect();
    this.source?.disconnect();
    await this.context?.close();
    this.stream?.getTracks().forEach(track => track.stop());
  }
}
