# simple-sampler
A simple app that stores the last 10 seconds of computer audio via WASAPI, and saves the recording on a keypress. 
Designed to make gathering music samples from the internet easy.

CURRENTLY A VERY SIMPLE SINGLE PYTHON FILE - REQUIRES 'PyAudioPatch' & 'keyboard' LIBRARIES
Will sort out dependencies when the app is more fleshed out.

### How to use:
With dependencies installed, simply run 'recorder_with_keypress'. 
After at least 10 seconds of computer audio has been played, press 'a' to save the last 10 seconds as a .wav file.
These files are located in tmp/ , as numbered output.wav files.
These will be overwritten next time the app is opened, so move them somewhere else if you care!

### Planned updates:
 - UI
 - Settings (keybind remapping, length of audio buffer)
 - Simple waveform editor (select start / stop points, maybe some FX?)