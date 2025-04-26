#!/usr/bin/env python
# Copyright 2025 Grant Marshall
import argparse
from datetime import datetime
import numpy
import queue
import random
import sounddevice as sd
import soundfile as sf
import sox
import string
import sys


def parse_args():
    """Helper function for argument parsing."""

    def int_or_str(text):
        try:
            return int(text)
        except ValueError:
            return text

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "-l",
        "--list-devices",
        action="store_true",
        help="show list of audio devices and exit",
    )
    # Parse any args that short-circuit and don't actually run the recorder
    args, remaining = parser.parse_known_args()
    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)

    # Parse the remaining args required for recording
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[parser],
    )
    parser.add_argument(
        "-d", "--device", type=int_or_str, help="input device (numeric ID or substring)"
    )
    parser.add_argument("-r", "--samplerate", type=int, help="sampling rate")
    parser.add_argument("-c", "--channels", type=int, help="number of input channels")
    parser.add_argument(
        "-t", "--time", type=int, help="number of seconds to record", default=5
    )
    parser.add_argument(
        "-o", "--outputfile", type=str, help="output file to write the wav to"
    )
    unverified_args = parser.parse_args(remaining)
    # Check that all required args for recording are provided, and if not,
    # add a helpful message and error out
    return unverified_args


def main():
    """Entry point of the recording frontend for hush-subtitles"""
    args = parse_args()
    if args.device is not None:
        if args.samplerate is None:
            device_info = sd.query_devices(args.device, "input")
            args.samplerate = int(device_info["default_samplerate"])
        if args.channels is None:
            device_info = sd.query_devices(args.device, "input")
            args.channels = int(device_info["max_input_channels"])
        if args.outputfile is None:
            temporary_tag = "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(10)
            )
            args.outputfile = "temp_rec_" + temporary_tag + ".wav"
        print(args.outputfile)

        block_queue = queue.Queue()
        frame_buffer = []

        def callback(indata, frames, time, status):
            if status:
                print(status, file=sys.stderr)
            block_queue.put(numpy.copy(indata))

        with sd.InputStream(
            samplerate=args.samplerate,
            device=args.device,
            channels=args.channels,
            callback=callback,
        ):
            while len(frame_buffer) < args.time * args.samplerate:
                frame_buffer += list(block_queue.get())
        tfm = sox.Transformer()
        tfm.set_output_format(channels=1, rate=16000)
        downsampled_audio = tfm.build_array(
            input_array=numpy.copy(frame_buffer), sample_rate_in=args.samplerate
        )

        with sf.SoundFile(
            args.outputfile, mode="x", samplerate=16000, channels=1, subtype="PCM_24"
        ) as file:
            file.write(downsampled_audio.astype(numpy.float32))


main()
