from pathlib import Path
from typing import Any, List, Tuple
import wave
import numpy as np


def read_pcm(filename: Path):
    """Read PCM file into numpy array. Assuming 16-bit mono PCM."""
    return np.fromfile(filename, dtype=np.int16)


def write_wav(data, filename, sample_rate):
    """Write a NumPy array to a WAV file."""
    with wave.open(str(filename), "wb") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16 bits per sample
        wf.setframerate(sample_rate)
        wf.writeframes(data.astype(np.int16).tobytes())


def combine_pcm_to_wav(pcm_root_path, output_filename, sample_rate=16000):
    files_data: List[Tuple[int, Any]] = []
    max_time_ms = 0

    # Collect all PCM files and their start times

    for file in Path.iterdir(pcm_root_path):
        if (
            file.is_file()
            and file.suffix == ".pcm"
            and not file.name.endswith("_tmp.pcm")
        ):
            _, start = file.stem.split("_", 1)
            data = read_pcm(file)
            offset_ms = int(start)
            duration_ms = len(data) * 1000 / sample_rate
            end_time_ms = offset_ms + duration_ms
            files_data.append((offset_ms, data))
            if end_time_ms > max_time_ms:
                max_time_ms = end_time_ms

    # Create a large enough buffer to hold the entire session
    total_samples = int(sample_rate * max_time_ms / 1000)
    combined_audio = np.zeros(total_samples, dtype=np.float32)

    # Combine all audio files
    for start, data in files_data:
        start_sample = int(sample_rate * start / 1000)
        end_sample = start_sample + len(data)
        combined_audio[start_sample:end_sample] += data

    # Normalize audio to prevent clipping
    max_val = np.max(np.abs(combined_audio))
    if max_val > 32767:
        combined_audio *= 32767 / max_val

    # Save the combined audio to a WAV file
    write_wav(combined_audio, output_filename, sample_rate)
