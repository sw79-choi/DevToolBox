# -*- coding: utf-8 -*-
"""Capture whatever the PC is currently playing and encode it to MP3.

Windows-only: PyAudioWPatch adds WASAPI loopback recording to PyAudio, so the
"input" device here is really the system's output mixed down to a stream.
Encoding goes through lameenc (a self-contained libmp3lame binding), so no
external ffmpeg install is required.
"""
from __future__ import annotations

import os
import time
from typing import Callable, Dict, List, Optional

CHUNK = 1024


def format_elapsed(seconds: float) -> str:
    total = max(int(seconds), 0)
    return "%02d:%02d" % (total // 60, total % 60)


def list_output_devices() -> List[Dict]:
    """Every playback device that can be captured as a WASAPI loopback source."""
    import pyaudiowpatch as pyaudio

    devices = []
    with pyaudio.PyAudio() as pa:
        for info in pa.get_loopback_device_info_generator():
            devices.append({
                "index": info["index"],
                "name": info["name"],
                "channels": int(info["maxInputChannels"]),
                "sample_rate": int(info["defaultSampleRate"]),
            })
    return devices


def _resolve_device(pa, pyaudio, device_index: Optional[int]):
    if device_index is not None:
        return pa.get_device_info_by_index(device_index)

    wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
    speakers = pa.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
    if speakers.get("isLoopbackDevice"):
        return speakers
    for loopback in pa.get_loopback_device_info_generator():
        if speakers["name"] in loopback["name"]:
            return loopback
    raise RuntimeError("No loopback device found for the default output device.")


_POLL_SECONDS = 0.2


def record_to_mp3(
    output_path: str,
    device_index: Optional[int] = None,
    bitrate: int = 192,
    should_cancel: Optional[Callable[[], bool]] = None,
    message: Optional[Callable[[str], None]] = None,
) -> Dict:
    """Record system audio until should_cancel() is true, then finish the MP3 file.

    The stream is opened with a callback instead of blocking reads: WASAPI
    loopback only invokes the callback while the device is actually rendering
    audio, so a plain `stream.read()` loop can stall for as long as the PC
    stays silent - the Stop button (and the device picker, disabled while
    "busy") would then never come back. Polling should_cancel() on a timer
    here is independent of whether any audio ever arrives.
    """
    import lameenc
    import pyaudiowpatch as pyaudio

    output_path = os.path.abspath(output_path)
    folder = os.path.dirname(output_path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with pyaudio.PyAudio() as pa:
        device = _resolve_device(pa, pyaudio, device_index)
        channels = int(device["maxInputChannels"]) or 2
        rate = int(device["defaultSampleRate"])

        encoder = lameenc.Encoder()
        encoder.set_bit_rate(bitrate)
        encoder.set_in_sample_rate(rate)
        encoder.set_channels(channels)
        encoder.set_quality(2)

        handle = open(output_path, "wb")
        frames_captured = 0

        def callback(in_data, frame_count, time_info, status):
            nonlocal frames_captured
            frames_captured += frame_count
            handle.write(encoder.encode(in_data))
            return (None, pyaudio.paContinue)

        stream = pa.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=device["index"],
            frames_per_buffer=CHUNK,
            stream_callback=callback,
        )

        started = time.time()
        try:
            while not (should_cancel and should_cancel()):
                if message:
                    message("Recording... %s" % format_elapsed(time.time() - started))
                time.sleep(_POLL_SECONDS)
        finally:
            stream.stop_stream()
            stream.close()
            # lameenc only "starts" on the first encode() call; flushing before
            # that (nothing was ever captured, e.g. the PC stayed silent) raises.
            if frames_captured:
                handle.write(encoder.flush())
            handle.close()

    return {
        "output_path": output_path,
        "seconds": time.time() - started,
        "device_name": device["name"],
        "frames_captured": frames_captured,
    }
