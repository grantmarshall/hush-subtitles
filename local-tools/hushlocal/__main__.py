import argparse
from datetime import datetime
import numpy
import queue
import sounddevice as sd
import sox
import sys
import whisper


def parse_args():
    """Helper function for argument parsing."""

    def int_or_str(text):
        try:
            return int(text)
        except ValueError:
            return text

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        '-l', '--list-devices', action='store_true',
        help='show list of audio devices and exit')
    args, remaining = parser.parse_known_args()
    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[parser])
    parser.add_argument(
        '-d', '--device', type=int_or_str,
        help='input device (numeric ID or substring)')
    parser.add_argument(
        '-r', '--samplerate', type=int, help='sampling rate')
    parser.add_argument(
        '-c', '--channels', type=int, help='number of input channels')
    parser.add_argument(
        '-m',
        '--model',
        type=str,
        help='whisper model to use',
        default='medium'
    )
    parser.add_argument(
        '-w',
        '--windowsize',
        type=int,
        help='seconds of audio to pass into the model each translation',
        default=30
    )
    parser.add_argument(
        '-tl',
        '--translationlatency',
        type=int,
        help='seconds after a translation before another starts',
        default=5
    )
    return parser.parse_args(remaining)


def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    assert len(indata) == frames
    block_queue.put(numpy.copy(indata))


args = parse_args()
# The number of frames in a window
input_width = args.samplerate * args.windowsize
# The number of frames to trim the buffer to after processing
remainder_width = args.samplerate * (args.windowsize - args.translationlatency)

print('Loading Model')
model = whisper.load_model(args.model)
print('Model Loaded')

# Will contain numpy arrays with the blocks of audio as they pass through
block_queue = queue.Queue()
# Will be a list of frames the be packed into a numpy array and processed
frame_buffer = []

if args.samplerate is None:
    device_info = sd.query_devices(args.device, 'input')
    # soundfile expects an int, sounddevice provides a float:
    args.samplerate = int(device_info['default_samplerate'])
print("Starting recording")
tfm = sox.Transformer()
tfm.set_output_format(channels=1, rate=16000)
with sd.InputStream(
        samplerate=args.samplerate,
        device=args.device,
        channels=args.channels,
        callback=callback):
    while True:
        # Add audio frames from the callback function to the end of the buffer
        frame_buffer += list(block_queue.get())

        # If there's at least 30 seconds of audio in the buffer, trigger
        if (block_queue.qsize() == 0 and len(frame_buffer) >= input_width):
            now = datetime.now()

            # Clone last input_width frames into a copy to pass to the model
            window_copy = numpy.copy(frame_buffer[-1 * input_width:])

            # Trim the buffer down below input_width to allow frames to flow in
            frame_buffer = frame_buffer[-1 * remainder_width:]

            downsampled_data = tfm.build_array(
                input_array=window_copy,
                sample_rate_in=args.samplerate)

            # Transcribe/translate the downsampled audio
            print('Translation cut at:', now)
            print('Translation Beginning')
            result = whisper.transcribe(
                        audio=downsampled_data.astype(numpy.float32),
                        model=model,
                        task="translate")
            print(result['text'])
            print('Translation complete')