# local-tools

This folder contains tools intended to run locally to debug/use whisper for 
live subtitling or translating locally. You could use this to translate streams 
you're watching or add translations/transcriptions of your desktop audio to the 
screen for capture in obs as examples of why this might be useful.

My plans for this are to give it a simple Tk GUI mode to make it a little more 
easy to use as an actual subtitling tool, along with the option to generate an 
actual subtitle file to be used later in a non-streaming fashion if desired.

This is not ultimately intended to be the most robust solution. Once this is 
polished a little bit, I'll move back to focusing on the web app version of 
this concept which should be better in many ways.

## Setup instructions

Windows:

1. Install python, pip, [SoX](https://sourceforge.net/projects/sox/), and git.
2. Clone this repository.
3. Make a virtualenv and install the requirements.
4. Make sure to use cuda-accelerated torch by running the appropriate pip
   command from [here](https://pytorch.org/get-started/locally/).
5. (Optional) Set up a virtual audio cable so you can pipe the audio from your 
   PC to the hushlocal script.
6. Run `python hushlocal --help` from the local-tools directory for further 
   details on the actual command.
