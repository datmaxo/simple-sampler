# simple-sampler
A simple app that stores the last 10 seconds of computer audio via WASAPI, and saves the recording on a keypress. 
Designed to make gathering music samples from the internet easy.
 
---

### How to use:

1. Clone the repository to your local machine via `git clone git@github.com:datmaxo/simple-sampler.git`
2. After copying the repository, simply execute `simplesampler.exe`; startup may take a few moments
3. Once loaded, press the green 'start recording' button, or alternatively press Enter, to reach the main editor window.
4. To begin recording the background audio, press the record button. Then, press the 'save last n seconds' button to create clips as you desire, or use the customisable keyboard shortcut.
5. To edit and export audio once recorded, select the region in the clip's editor window that you wish to save with the left and right mouse buttons. Then, simply use the 'export selection' button.
   You can zoom in and out along the recording using the scrollwheel, if additional precision is desired.

---

### Using the code / making changes:

All code for the project is found under the `\sampler\` directory - `simplesampler.pyw` merely serves to open `\sampler\start_screen.py`, and acts as a target for pyinstaller.
To rebuild `simplesampler.exe`, simply run `build.sh` from the main directory. Be aware that this script will require the python module `pyinstaller` to be successful.

---

### Planned Updates:

At this point, I've added most of the major functionality that I want to for this application.
There are a few issues with the code I may refactor down the line, and I'm not fully satisfied with the speed of some operations right now, so I may work to improve those.

Additionally, while matplotlib works fine for the audio-visualisation backend, I don't think it's been the most efficient choice of graphics library.
I may work to visualise the recordings using tkinter directly, or find some other UI-intergratable graphics library in the future, but I'm okay with things as they stand right now to this end. 
