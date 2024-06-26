"""
IMPORTATNT: keyboard.read_key() runs the hotkey processes in its native thread!
This causes issues when using it to save files, as matplotlib gets angry.
Solution; we queue saved files to be rendered in MainEditor when out of focus,
and render when we maximise the window again :)

I also think we have to block playblack whilst recording sadly; it just doesn't work well.
For now, we can just make a new Recorder on minimisation, and delete them on focus.
"""

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from functools import partial
import keyboard
import pyaudiowpatch as pyaudio #allows WASAPI
import numpy as np
import sys
import wave

from passive_recorder import Recorder
from wave_editor import EditorWindow
from threading import Thread

"""This should really be its own script but for now it can stay here"""
class MainEditor ():
    def __init__ (self, rec_set, binds, open_immeditately = []):
        self.p = pyaudio.PyAudio()
        self.rec_args = rec_set
        self.tabs = []
        self.tab_frames = []
        self.recording_num = 1
        self.clip_queue = []
        self.focused = True
        self.offFocus()
        
        #main window
        self.root = tk.Tk()
        self.root.geometry("750x300")
        self.root.title(f"Editor")
        self.root.configure(bg='white', padx=10, pady=10)

        #file manager
        self.tabControl = ttk.Notebook(self.root, width=500) 
        self.tabControl.pack(side = 'left', expand = False, fill = "y")

        self.editFrame = tk.Frame(self.root, width = 250, relief='ridge', borderwidth = 3,
                                  bg='#c9c9c9', padx=10, pady=10)
        self.editFrame.pack(side='right', fill='y')
        self.editFrame.pack_propagate(0)
        exportButton = tk.Button(self.editFrame, height = 1, text='Export Selection',
                                 command=self.exportSelection)
        exportButton.pack(side='bottom', fill = 'x')

        for x in open_immeditately: self.addClip(x)
        keyboard.add_hotkey(binds['save'], self.save_recording)
        keyboard.add_hotkey(binds['exit'], self.exit)

        self.root.bind("<space>", self.play)
        self.root.bind("<FocusIn>", self.onFocus)
        self.root.bind("<FocusOut>", self.offFocus)

        self.root.wm_state('iconic') #is starting as minimised worth? make this a setting
        self.root.mainloop()

    #get the active notebook tab
    def getActive (self):
        return self.tabControl.index(self.tabControl.select())

    def exit (self):
        #something something
        self.root.destroy()
        exit()

    """w/ this structure I won't ever need to save temp files; i can just pass the recorded aud to the editor
       I think i'm going to keep doing it just for backup reasons tho"""
    def save_recording (self):
        out = self.recorder.write_file(self.recording_num)
        if out != None:
            if not self.focused:
                self.clip_queue.append(np.array(out))
            else:
                self.addClip(np.array(out))
        print('Recording saved.')

    def addClip (self, audio):
        self.tab_frames.append(ttk.Frame(self.tabControl))
        self.tabControl.add(self.tab_frames[-1], text = f'untitled ({self.recording_num}).wav')
        self.tabs.append(EditorWindow(self.tab_frames[-1], audio, self.rec_args))
        self.recording_num += 1

    #should set 'playable' flag in other threads to prevent overwhemling the buffer
    def play (self, _=''):
        self.tabs[self.getActive()].start_play_thread()

    def exportSelection (self):
        data = self.tabs[self.getActive()].saveSelection()
        name = fd.asksaveasfilename(defaultextension=".wav", filetypes=[("Wave Files", ".wav")])
        self.tabControl.tab(self.getActive(), text = name.split('/')[-1])
        print(data[0])

        with wave.open(name, 'wb') as wf:
            wf.setnchannels(self.rec_args['CHANNELS'])
            wf.setsampwidth(self.p.get_sample_size(self.rec_args['FORMAT']))
            wf.setframerate(self.rec_args['RATE'])
            #for x in data:
            wf.writeframes(data) #write data to wav

        print(f'Exported selection to {name}')

    #called on maximising; ends recording, draws newly recorded files
    def onFocus (self, _=''):
        if not self.focused:
            self.focused = True
            try: self.recorder.stop = True
            except: print("Couldn't stop recording - no recorder loaded :(")
            for x in self.clip_queue: self.addClip(x)
            self.clip_queue = []
            self.root.update_idletasks()
            print('focused')

    #called on minimising; start a new recorder
    def offFocus (self, _=''):
        if self.focused:
            self.focused = False
            self.recorder = Recorder(self.rec_args)
            print('waa. it is blury')


if __name__ == '__main__':

    rec_args = {'CHUNK': 4, 
        'FORMAT': pyaudio.paInt16,
        'RATE':48000,
        'CHANNELS': 1 if sys.platform == 'darwin' else 2,
        'RECORD_SECONDS': 10
    }
    binds = {'save': 'ctrl+alt+s', 'exit': 'ctrl+alt+e'}

    widnow = MainEditor(rec_args, binds, ['tmp/output(1).wav'])
