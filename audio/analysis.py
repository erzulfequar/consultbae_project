"""Server-side audio metadata extraction."""

import math

import numpy as np
import soundfile as sf
from mutagen import File as mutagen_file


def extract_audio_analysis(file_path):
    """Return duration, sample rate, bitrate, channels, and mean loudness.

    The decoders read the stored file, so this works independently of the
    browser and reliably persists metadata for every supported upload.
    """
    try:
        info = mutagen_file(file_path).info
        result = {
            "duration_seconds": float(info.length),
            "sample_rate_hz": int(info.sample_rate),
            "channels": int(info.channels),
        }
        if getattr(info, "bitrate", None):
            result["bitrate_kbps"] = float(info.bitrate) / 1000

        # Estimate the quietest 10% of windows, expressed in dBFS.
        window_rms = []
        squared_total = 0.0
        sample_count = 0
        for block in sf.blocks(file_path, blocksize=2048, always_2d=True):
            squared_total += float(np.sum(np.square(block)))
            sample_count += block.size
            window_rms.append(float(np.sqrt(np.mean(np.square(block)))))
        if sample_count:
            result["loudness_dbfs"] = 20 * math.log10(
                max(math.sqrt(squared_total / sample_count), 0.000001)
            )
        if window_rms:
            window_rms.sort()
            quietest = window_rms[:max(1, math.ceil(len(window_rms) * 0.1))]
            result["noise_floor_dbfs"] = 20 * math.log10(max(sum(quietest) / len(quietest), 0.000001))
        return result
    except (OSError, RuntimeError, ValueError, AttributeError):
        return {}
