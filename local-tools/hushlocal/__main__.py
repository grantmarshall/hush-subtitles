#!/usr/bin/env python
# Copyright 2025 Grant Marshall
import argparse
from datetime import datetime, timedelta
from enum import Enum
import numpy
import psycopg2
import queue
import random
import sounddevice as sd
import soundfile as sf
import sox
import string
import sys
import uuid


DATABASE_NAME = "whisper"
DATABASE_PORT = 5432
DATA_INSERTION_SQL_STATEMENT = """
INSERT INTO audio_data (session_id, start_ts, d)
VALUES (%s, %s, %s)
"""
SESSION_CREATION_SQL_STATEMENT = """
INSERT INTO sessions (id, active, creation_time, last_translation)
VALUES (%s, %s, %s, %s)
"""
SESSION_CLOSE_SQL_STATEMENT = """
UPDATE sessions SET active = 'False' WHERE id=%s
"""


class Mode(Enum):
    """Enum for different frontend modes"""

    local_record = 1
    retrieve = 2
    translate = 3


def parse_args():
    """Helper function for argument parsing."""

    def int_or_str(text):
        try:
            return int(text)
        except ValueError:
            return text

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
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
        "--mode", choices=["local_record", "retrieve", "translate"], required=True
    )
    parser.add_argument(
        "--device",
        type=int_or_str,
        help="input device (numeric ID or substring)",
        required=True,
    )
    parser.add_argument("--samplerate", type=int, help="sampling rate")
    parser.add_argument("--channels", type=int, help="number of input channels")
    parser.add_argument(
        "--time", type=int, help="number of seconds to record", default=5
    )
    parser.add_argument(
        "--outputfile", type=str, help="output file to write the wav to"
    )
    parser.add_argument("--host", type=str, help="host name of the database to use")
    parser.add_argument("--password", type=str, help="password for the database")
    parser.add_argument("--user", type=str, help="user for the database")
    unverified_args = parser.parse_args(remaining)
    # Check that all required args for recording are provided, and if not,
    # add a helpful message and error out
    return unverified_args


def main():
    """Entry point of the recording frontend for hush-subtitles"""
    args = parse_args()
    mode = Mode[args.mode]
    match mode:
        case Mode.local_record:
            local_record(args)
        case Mode.translate:
            translate(args)
        case Mode.retrieve:
            print("Not implemented")
        case _:
            print("Please provide a valid mode")


def local_record(args):
    """Function for recording audio and saving locally"""
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
        """Called by sounddevice for each indata chunk"""
        if status:
            print(status, file=sys.stderr)
        assert len(indata) == frames
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
        input_array=numpy.copy(frame_buffer[: args.time * args.samplerate]),
        sample_rate_in=args.samplerate,
    )

    with sf.SoundFile(
        args.outputfile, mode="x", samplerate=16000, channels=1, subtype="PCM_24"
    ) as file:
        file.write(downsampled_audio.astype(numpy.float32))


def translate(args):
    """Record from an audio device, store it in the db, and retrieve translations"""
    if args.samplerate is None:
        device_info = sd.query_devices(args.device, "input")
        args.samplerate = int(device_info["default_samplerate"])
    if args.channels is None:
        device_info = sd.query_devices(args.device, "input")
        args.channels = int(device_info["max_input_channels"])

    session_uuid = uuid.uuid4()
    session_creation_time = datetime.now()
    connection = psycopg2.connect(
        database=DATABASE_NAME,
        user=args.user,
        password=args.password,
        host=args.host,
        port=DATABASE_PORT,
    )
    session_cursor = connection.cursor()
    session_cursor.execute(
        SESSION_CREATION_SQL_STATEMENT,
        (str(session_uuid), True, session_creation_time, session_creation_time),
    )
    connection.commit()

    block_queue = queue.Queue()
    frame_buffer = []

    def callback(indata, frames, time, status):
        """Called by sounddevice for each indata chunk"""
        if status:
            print(status, file=sys.stderr)
        assert len(indata) == frames
        block_queue.put(numpy.copy(indata))

    data_cursor = connection.cursor()
    current_translation_time = session_creation_time

    with sd.InputStream(
        samplerate=args.samplerate,
        device=args.device,
        channels=args.channels,
        callback=callback,
    ):
        try:
            while True:
                # fill the framebuffer with at least a second of audio data
                while len(frame_buffer) < args.samplerate:
                    frame_buffer += list(block_queue.get())

                # downsample the audio to the input rate of whisper then clean the frame buffer
                tfm = sox.Transformer()
                tfm.set_output_format(channels=1, rate=16000)
                downsampled_audio = tfm.build_array(
                    input_array=numpy.copy(frame_buffer),
                    sample_rate_in=args.samplerate,
                )
                frame_buffer = frame_buffer[args.samplerate :]
                # TODO: insert the downsampled data into the database
                print("Inserting data")
                data_cursor.execute(
                    DATA_INSERTION_SQL_STATEMENT,
                    (str(session_uuid), current_translation_time, downsampled_audio.tolist()),
                )
                connection.commit()
                current_translation_time = current_translation_time + timedelta(seconds=1)

        except KeyboardInterrupt:
            print("Cleaning up")
            data_cursor.close()
            session_cursor.execute(SESSION_CLOSE_SQL_STATEMENT, (str(session_uuid),))
            connection.commit()
            session_cursor.close()
            connection.close()
            print("Session closed")


main()
