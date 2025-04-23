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

(Out of date)

New version will have the recording script run in base windows, writing to a
SQL datastore while the translation script runs as a daemon in WSL. Expect to
get this up and running by 4/24, will include updated instructions then.
