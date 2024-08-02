"""
IMPORTATNT: keyboard.read_key() runs the hotkey processes in its native thread!
This causes issues when using it to save files, as matplotlib gets angry.
Solution; we queue saved files to be rendered in MainEditor when out of focus,
and render when we maximise the window again :)

I also think we have to block playblack whilst recording sadly; it just doesn't work well.
For now, we can just make a new Recorder on minimisation, and delete them on focus.
"""

#TODO: this editor could probably be way more memory efficient if I only load audio as its required and also
#unload audio for frames that are not currently being edited

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
from settings import SettingsWin
from keybind import KeybindsWin
from threading import Thread

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk)

#matplotlib rendering params; we don't particualrly care for accuarcy compared to performance here
mpl.rcParams['path.simplify'] = True
mpl.rcParams['path.simplify_threshold'] = 1
mpl.use('TkAgg')

"""This should really be its own script but for now it can stay here"""
class MainEditor ():
    def __init__ (self, rec_set, binds, open_immeditately = [], root=''):
        self.p = pyaudio.PyAudio()
        self.rec_args = rec_set
        self.tabs = []
        self.tab_frames = []
        self.recording_num = 1
        self.clip_queue = []
        self.focused = True
        self.loop = False
        self.recording = False #are we recording audio right now?
        self.offFocus()
        
        #main window; can be passes the root of the startUI to keep things within one window
        if root != '':
            self.root = root
        else:
            self.root = tk.Tk()
        self.root.geometry("750x300")
        self.root.title(f"Editor")
        self.root.configure(bg='white', padx=10, pady=10)

        #file manager
        self.tabControl = ttk.Notebook(self.root, width=500) 
        self.tabControl.pack(side = 'left', expand = False, fill = "y")

        #matplotlib stuff - pass to each editorwindow to keep memory usage down :)
        self.fig, self.ax = plt.subplots(nrows=2, ncols=1)

        #editor options frame
        self.editFrame = tk.Frame(self.root, width = 250, relief='ridge', borderwidth = 3,
                                  bg='#c9c9c9', padx=10, pady=10)
        self.editFrame.pack(side='right', fill='y')
        self.editFrame.pack_propagate(0)

        mainbuttons = tk.Frame(self.editFrame, width = 250, height=60)
        mainbuttons.pack(side='top')
        mainbuttons.pack_propagate(0)
        playButton = tk.Button(mainbuttons, height=3, text="Play", command=self.play)
        playButton.pack(side='left', fill='x', expand=True)
        stopButton = tk.Button(mainbuttons, height=3, text="Stop", command=self.stop)
        stopButton.pack(side='left', fill='x', expand=True)
        self.loopButton = tk.Button(mainbuttons, height=3, text="Loop", command=self.setLoop)
        self.loopButton.pack(side='left', fill='x', expand=True)
        self.recButton = tk.Button(mainbuttons, height=3, text="Rec ", command=self.record)
        self.recButton.pack(side='left', fill='x', expand=True)
        self.menuInit()

        #button for saving last n seconds of recorded audio; only enabled when recording of course!
        self.saveRecBut = tk.Button(self.editFrame, height = 1, text=f"Save Last {self.rec_args['RECORD_SECONDS']}s",
                                 command=self.save_recording)
        self.saveRecBut.pack(side='top', fill = 'x')
        self.saveRecBut['state'] = 'disabled'

        closeButton = tk.Button(self.editFrame, height = 1, text='Close Current Recording',
                                 command=self.closeRecording)
        closeButton.pack(side='bottom', fill = 'x')
        exportButton = tk.Button(self.editFrame, height = 1, text='Export Selection',
                                 command=self.exportSelection)
        exportButton.pack(side='bottom', fill = 'x')
        setButton = tk.Button(self.editFrame, height = 1, text='Change Settings',
                                 command=self.openSettings)
        setButton.pack(side='bottom', fill = 'x')

        #buttons that are disabled when the module is recording
        self.buttonsToDisable = [playButton, stopButton, closeButton, exportButton, setButton]

        for x in open_immeditately: self.addClip(x)
        keyboard.add_hotkey(binds['save'], self.save_recording)
        keyboard.add_hotkey(binds['exit'], self.exit)

        self.root.bind("<space>", self.play)
        self.root.bind("<FocusIn>", self.onFocus)
        self.root.bind("<FocusOut>", self.offFocus)

        if True:
            self.tabs[self.getActive()].onFocus()
        else: self.root.wm_state('iconic') #is starting as minimised worth? make this a setting
        self.setLoop() #i think looping is fun and therefore it's nice to have it on by default
        
        self.root.mainloop()

    def menuInit (self):
        self.bar = tk.Menu(self.root)
        
        options = tk.Menu(self.bar, tearoff=0)
        options.add_command(label='Edit Settings', command=self.openSettings)
        options.add_command(label='Edit Keybinds', command=self.openKeybinds)
        
        self.bar.add_cascade(menu=options, label='Options')
        self.root.config(menu=self.bar)

    #get the active notebook tab
    def getActive (self):
        return self.tabControl.index(self.tabControl.select())

    #opens the settings module as a toplevel tk window
    def openSettings (self):
        self.setWin = tk.Toplevel()
        self.setWin.title('Settings')
        SettingsWin(self.rec_args, self.setWin, self.updateSettings)

    #opens the keybinds module as a toplevel tk window
    def openKeybinds (self):
        self.kbWin = tk.Toplevel()
        self.kbWin.title("Alter Keybindings")
        KeybindsWin(self.kbWin, self.reloadBinds)

    #updates the settings to the new values, destroys the toplevel settings window
    #could instead store a list of immutable setting titles in the tabs, and change all others - this should work fine
    #but that would be a better system, so maybe switch it up at a later date
    def updateSettings (self, newsettings):
        self.rec_args = newsettings

        #destroy the settings window
        try: self.setWin.destroy()
        except: print('No settings window to destroy!')

        #try and update the values of target settings in each tab 
        try:
            for tab in self.tabs:
                tab.updateSettings({'USE_MESSAGE_BOXES': newsettings['USE_MESSAGE_BOXES']})
        except Exception as e:
            print(f'Specified setting was not found: {e}')

    #reloads the keybinds from file, destroys toplevel. doesn't currently re-load settings if they have been lost.
    def reloadBinds (self):
        with open('data/keybinds.json', 'r+') as keyfile:
            kb = keyfile.read()
            if len(kb) == 0:
                print("No keybind file found - saving default binds.")
                keyfile.write(json.dumps(self.binds))
            else:
                self.binds = json.loads(kb)
                print("Keybinds loaded.")

        try: self.kbWin.destroy()
        except: print('No keybinds window to destroy!')

    def exit (self):
        #something something
        self.root.destroy()
        exit()

    """w/ this structure I won't ever need to save temp files; i can just pass the recorded aud to the editor
       I think i'm going to keep doing it just for backup reasons tho"""
    def save_recording (self):
        out = self.recorder.write_file(self.recording_num)
        self.recording_num += 1
        if out != None:
            self.addClip(out)
        print('Recording saved.')

    def addClip (self, path):
        self.tab_frames.append(ttk.Frame(self.tabControl))
        self.tabControl.add(self.tab_frames[-1], text = f'untitled ({self.recording_num}).wav')
        self.tabs.append(EditorWindow(self.tab_frames[-1], path, self.rec_args, self.fig, self.ax))

    #should set 'playable' flag in other threads to prevent overwhemling the buffer
    def play (self, _=''):
        self.tabs[self.getActive()].start_play_thread()

    def stop (self, _=''):
        self.tabs[self.getActive()].stop()

    def setLoop (self, _=''):
        self.loop = not self.loop
        if self.loop:
            self.loopButton.configure(relief='sunken')
        else:
            self.loopButton.configure(relief='raised')
        print(f'Loop has been set to {self.loop}')
        for tab in self.tabs:
            tab.setLoop(self.loop)

    #either enables or disables recording, depending on the state of self.recording
    #most of this code replaces the roles of onFocus and offFocus
    def record (self, _=''):
        self.recording = not self.recording
        if self.recording:
            self.stop()
            self.recButton.configure(relief='sunken')
            self.saveRecBut['state'] = 'normal'
            for b in self.buttonsToDisable: b['state'] = 'disabled'

            self.recorder = Recorder(self.rec_args)
            if self.rec_args["MINIMIZE_ON_RECORD"]:
                self.root.wm_state('iconic')
            
        else:
            self.recButton.configure(relief='raised')
            self.saveRecBut['state'] = 'disabled'
            for b in self.buttonsToDisable: b['state'] = 'normal'

            try: self.recorder.stop = True
            except: print("Couldn't stop recording - no recorder loaded :(")
            for x in self.clip_queue: self.addClip(x)
            self.tabs[self.getActive()].onFocus()
            self.clip_queue = []
            self.root.update_idletasks()

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

    #closes the current recording window
    def closeRecording (self):
        i = self.getActive()
        self.tabs[i].destroyEditor()

        #try and close the tab if it is; if it fails, we know it's been destroyed, and can safely remove it
        try:
            if self.tabs[i].closing: self.tabs.pop(i)
        except: self.tabs.pop(i)
        if self.tabs == []: print('all tabs are gone!')

    #called on maximising; ends recording, draws newly recorded files
    def onFocus (self, _=''):
        pass
        """
        if not self.focused:
            self.focused = True
            try: self.recorder.stop = True
            except: print("Couldn't stop recording - no recorder loaded :(")
            for x in self.clip_queue: self.addClip(x)
            self.tabs[self.getActive()].onFocus()
            self.clip_queue = []
            self.root.update_idletasks()
            print('focused')
        """

    #called on minimising; start a new recorder
    def offFocus (self, _=''):
        pass
        """
        if self.focused:
            self.focused = False
            self.recorder = Recorder(self.rec_args)
            print('waa. it is blury')
        """

if __name__ == '__main__':

    import json # for loading stuff

    rec_args = {'CHUNK': 4, 
        'FORMAT': pyaudio.paInt16,
        'RATE':48000,
        'CHANNELS': 1 if sys.platform == 'darwin' else 2,
        'RECORD_SECONDS': 10,
        'MINIMIZE_ON_RECORD': False
    }
    try:
        with open('data/settings.json', 'r+') as argfile:
            dat = argfile.read()
            rec_args = json.loads(dat)
            print("Keybinds loaded.")
    except:
        print('some error occured but whatevs girlie')

    binds = {'save': 'ctrl+alt+s', 'exit': 'ctrl+alt+e'}

    widnow = MainEditor(rec_args, binds, ['tmp/output(1).wav'])
