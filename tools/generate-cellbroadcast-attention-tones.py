#!/usr/bin/env python3
#
# Generate private Cell Broadcast public-warning attention tones.
#
# The generated Ogg Vorbis file is reserved for official Cell Broadcast
# emergency-alert handling. They must not be installed in normal ringtone,
# ambience, alarm, or generic notification sound locations.

import argparse
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave


SAMPLE_RATE = 48000
AMPLITUDE = 0.82
FADE_SECONDS = 0.005

ATTENTION_FILENAME = "cellbroadcast-attention-853-960.ogg"
ATTENTION_SERIAL = 0x43424154

ATTENTION_SEGMENTS = [
    ((853.0, 960.0), 2.0),
    ((), 0.5),
    ((853.0, 960.0), 1.0),
    ((), 0.5),
    ((853.0, 960.0), 1.0),
    ((), 0.5),
] * 2

# ETSI TS 102 900 requires a dedicated EU public-warning alerting indication,
# including audio. The published EU-Alert example uses the same simultaneous
# 853 Hz and 960 Hz two-tone signal as WEA, so generate one shared private asset
# and let metadata keep WEA and EU-Alert as separately selectable profiles.

OGG_CRC_LOOKUP = []
for value in range(256):
    crc = value << 24
    for _ in range(8):
        if crc & 0x80000000:
            crc = ((crc << 1) ^ 0x04c11db7) & 0xffffffff
        else:
            crc = (crc << 1) & 0xffffffff
    OGG_CRC_LOOKUP.append(crc)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True,
                        help="directory for generated Ogg Vorbis files")
    parser.add_argument("--encoder", default="auto",
                        help="Ogg Vorbis encoder executable, default: auto")
    return parser.parse_args()


def segment_samples(duration):
    return int(round(duration * SAMPLE_RATE))


def tone_sample(frequencies, index):
    if not frequencies:
        return 0.0
    value = 0.0
    for frequency in frequencies:
        value += math.sin(2.0 * math.pi * frequency * index / SAMPLE_RATE)
    return AMPLITUDE * value / float(len(frequencies))


def fade_factor(index, count):
    fade_samples = min(segment_samples(FADE_SECONDS), count // 2)
    if fade_samples <= 1:
        return 1.0
    if index < fade_samples:
        return index / float(fade_samples)
    remaining = count - index - 1
    if remaining < fade_samples:
        return remaining / float(fade_samples)
    return 1.0


def write_wav(path, segments):
    with wave.open(path, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)

        absolute_index = 0
        for frequencies, duration in segments:
            count = segment_samples(duration)
            frames = bytearray()
            for index in range(count):
                sample = tone_sample(frequencies, absolute_index)
                if frequencies:
                    sample *= fade_factor(index, count)
                sample = max(-1.0, min(1.0, sample))
                frames.extend(struct.pack("<h", int(round(sample * 32767.0))))
                absolute_index += 1
            output.writeframes(frames)


def resolve_encoder(encoder):
    if encoder != "auto":
        resolved = shutil.which(encoder)
        if not resolved:
            raise RuntimeError("%s not found" % encoder)
        return resolved

    for candidate in ("ffmpeg", "gst-launch-1.0"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise RuntimeError("no supported Ogg Vorbis encoder found")


def encode_ogg_ffmpeg(encoder, wav_path, ogg_path):
    command = [
        encoder,
        "-nostdin",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-fflags", "+bitexact",
        "-flags", "+bitexact",
        "-i", wav_path,
        "-map_metadata", "-1",
        "-vn",
        "-c:a", "libvorbis",
        "-q:a", "5",
        ogg_path,
    ]
    subprocess.check_call(command)


def encode_ogg_gstreamer(encoder, wav_path, ogg_path):
    command = [
        encoder,
        "-q",
        "filesrc", "location=" + wav_path,
        "!", "wavparse",
        "!", "audioconvert",
        "!", "audioresample",
        "!", "vorbisenc", "quality=0.5",
        "!", "oggmux",
        "!", "filesink", "location=" + ogg_path,
    ]
    subprocess.check_call(command)


def encode_ogg(encoder, wav_path, ogg_path):
    if os.path.basename(encoder) == "gst-launch-1.0":
        encode_ogg_gstreamer(encoder, wav_path, ogg_path)
    else:
        encode_ogg_ffmpeg(encoder, wav_path, ogg_path)


def ogg_crc(data):
    crc = 0
    for byte in data:
        crc = ((crc << 8) & 0xffffffff) ^ OGG_CRC_LOOKUP[((crc >> 24) & 0xff) ^ byte]
    return crc


def normalize_ogg(path, serial):
    with open(path, "rb") as source:
        data = bytearray(source.read())

    offset = 0
    while offset < len(data):
        if data[offset:offset + 4] != b"OggS":
            raise RuntimeError("invalid Ogg stream at offset %d" % offset)

        segment_count = data[offset + 26]
        header_length = 27 + segment_count
        payload_length = sum(data[offset + 27:offset + header_length])
        page_length = header_length + payload_length

        data[offset + 14:offset + 18] = struct.pack("<I", serial)
        data[offset + 22:offset + 26] = b"\0\0\0\0"
        data[offset + 22:offset + 26] = struct.pack(
            "<I", ogg_crc(data[offset:offset + page_length]))
        offset += page_length

    with open(path, "wb") as output:
        output.write(data)


def main():
    args = parse_args()
    try:
        encoder = resolve_encoder(args.encoder)
    except RuntimeError as error:
        sys.stderr.write(str(error) + "\n")
        return 1

    os.makedirs(args.output_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        wav_path = os.path.join(temp_dir, "attention.wav")
        ogg_path = os.path.join(args.output_dir, ATTENTION_FILENAME)
        write_wav(wav_path, ATTENTION_SEGMENTS)
        encode_ogg(encoder, wav_path, ogg_path)
        normalize_ogg(ogg_path, ATTENTION_SERIAL)

    return 0


if __name__ == "__main__":
    sys.exit(main())
