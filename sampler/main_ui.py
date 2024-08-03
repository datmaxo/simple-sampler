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
import os
import shutil
import keyboard
import pyaudiowpatch as pyaudio #allows WASAPI
import numpy as np
import sys
import wave

from sampler.passive_recorder import Recorder
from sampler.wave_editor import EditorWindow
from sampler.settings import SettingsWin
from sampler.keybind import KeybindsWin
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
    def __init__ (self, path, rec_set, binds, open_immeditately = [], root=''):
        self.path = path
        self.p = pyaudio.PyAudio()
        self.rec_args = rec_set
        self.tabs = []
        self.tab_frames = []
        self.recording_num = 1
        self.clip_queue = []
        self.focused = True
        self.loop = False
        self.recording = False #are we recording audio right now?
        self.empty = (len(open_immeditately) == 0) #do we have any recordings open right now?
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

        tk.Label(self.editFrame,pady=0, text='', bg='#c9c9c9').pack(side='top') #padding
        ampFrame = tk.Frame(self.editFrame, bg='#c9c9c9')
        ampFrame.pack(side='top', fill='x')
        ampText = tk.Label(ampFrame, text='Amplitude:', bg='#c9c9c9')
        ampText.pack(side='left')
        self.ampScale = tk.Scale(ampFrame, orient='horizontal', bg='#c9c9c9', bd=2, highlightthickness=0,
                                 command = partial(self.setAmp, ampText), showvalue = 0, troughcolor='#a9a9a9',
                                 from_=self.rec_args['MIN_AMP'], to=self.rec_args['MAX_AMP'],
                                 resolution = self.rec_args['AMP_RESOLUTION'] )
        self.ampScale.pack(side='right', fill='x')

        revBut = tk.Button(self.editFrame, height = 1, text=f"Reverse Selection",
                                 command=self.reverseSelection)
        revBut.pack(side='top', fill = 'x')

        closeButton = tk.Button(self.editFrame, height = 1, text='Close Current Recording',
                                 command=self.closeRecording)
        closeButton.pack(side='bottom', fill = 'x')
        exportButton = tk.Button(self.editFrame, height = 1, text='Export Selection',
                                 command=self.exportSelection)
        exportButton.pack(side='bottom', fill = 'x')
        setButton = tk.Button(self.editFrame, height = 1, text='Change Settings',
                                 command=self.openSettings)
        setButton.pack(side='bottom', fill = 'x')

        #buttons that are disabled when various conditions are met (recording, no recordings loaded)
        self.buttonsToDisable = {'Rec':[playButton, stopButton, closeButton, exportButton, setButton, revBut],
                                 'Empty': [playButton, stopButton, closeButton, exportButton, revBut],
                                 'Play': [revBut]}

        for x in open_immeditately: self.addClip(x)
        keyboard.add_hotkey(binds['save'], self.save_recording)
        keyboard.add_hotkey(binds['exit'], self.exit)

        self.root.bind("<space>", self.play)
        self.root.bind("<FocusIn>", self.onFocus)
        self.root.bind("<FocusOut>", self.offFocus)
        self.root.protocol("WM_DELETE_WINDOW", self.exit)

        #if we have no recordings pre-loaded, create an empty tab with some default 'no recordings loaded :(' text
        if self.empty:
            self.createEmptyTab()
        else:
            self.tabs[self.getActive()].onFocus()
        self.setLoop() #i think looping is fun and therefore it's nice to have it on by default
        #self.clearTempFiles()
        
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

    def createEmptyTab (self):
        self.empty = True
        self.setButtonsState('disabled', 'Rec')

        self.emptyFrame = ttk.Frame(self.tabControl)
        self.emptyFrame.pack()
        text = tk.Label(self.emptyFrame, text="\n\n\n\n\nNo recordings loaded :(\n\nPress the 'Rec' button to get started!")
        text.pack()

        self.tabControl.add(self.emptyFrame, text = ' ')

    def destroyEmptyTab (self):
        if self.empty:
            self.empty = False
            self.emptyFrame.destroy()
            if not self.recording: self.setButtonsState('normal', 'Empty')

    #opens the settings module as a toplevel tk window
    def openSettings (self):
        self.setWin = tk.Toplevel()
        self.setWin.title('Settings')
        SettingsWin(self.path, self.rec_args, self.setWin, self.updateSettings)

    #opens the keybinds module as a toplevel tk window
    def openKeybinds (self):
        self.kbWin = tk.Toplevel()
        self.kbWin.title("Alter Keybindings")
        KeybindsWin(self.path, self.kbWin, self.reloadBinds)

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
                
            self.ampScale.config(from_=self.rec_args['MIN_AMP'], to=self.rec_args['MAX_AMP'],
                                 resolution = self.rec_args['AMP_RESOLUTION'] )
        except Exception as e:
            print(f'Specified setting was not found: {e}')

    #reloads the keybinds from file, destroys toplevel. doesn't currently re-load settings if they have been lost.
    def reloadBinds (self):
        with open(os.path.join(self.path,'data/keybinds.json'), 'r+') as keyfile:
            kb = keyfile.read()
            if len(kb) == 0:
                print("No keybind file found - saving default binds.")
                keyfile.write(json.dumps(self.binds))
            else:
                self.binds = json.loads(kb)
                print("Keybinds loaded.")

        try: self.kbWin.destroy()
        except: print('No keybinds window to destroy!')

    #set a predetermined group of buttons to a specific state
    def setButtonsState(self, state, condition):
        for b in self.buttonsToDisable[condition]:
            b['state'] = state

    #quitting procedure for window closure; throws a message box if there are unsaved recordings
    def exit (self):
        unsaved = False
        msgOut = ''

        for f in self.tabs:
            if not f.saved: unsaved = True
        if unsaved and self.rec_args['USE_MESSAGE_BOXES']:
            msgOut = tk.messagebox.Message(message='You have unsaved recordings - do you really wish to quit?', type='yesno').show()
            
        if not unsaved or msgOut.lower() == 'yes':
            try:
                #self.clearTempFiles()
                self.root.destroy()
                sys.exit(0)
            except Exception as e:
                tk.messagebox.Message(message=f'Okay, the program does not want to quit...\n{e}', type='ok').show()

    """w/ this structure I won't ever need to save temp files; i can just pass the recorded aud to the editor
       I think i'm going to keep doing it just for backup reasons tho"""
    def save_recording (self):
        out = self.recorder.write_file(self.recording_num)
        self.recording_num += 1
        if out != None:
            self.addClip(out)
        print('Recording saved.')

    #clears the contents of the tmp folder
    #shout-out to https://stackoverflow.com/questions/185936/how-to-delete-the-contents-of-a-folder
    def clearTempFiles (self):
        path = os.path.realpath(os.path.dirname(__file__)) + '\\tmp'
        for filename in os.listdir(path):
            print(filename)
            if filename != 'root.tmp':
                file_path = os.path.join(path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print('Failed to delete %s. Reason: %s' % (file_path, e))

    def addClip (self, path):
        self.tab_frames.append(ttk.Frame(self.tabControl))
        self.tabControl.add(self.tab_frames[-1], text = f'untitled ({self.recording_num}).wav')
        self.tabs.append(EditorWindow(self.path, self.tab_frames[-1], path, self.rec_args, self.fig, self.ax, onFocusFuncs=[self.getAmp]))
        if self.empty:
            self.destroyEmptyTab()

    #should set 'playable' flag in other threads to prevent overwhemling the buffer
    def play (self, _=''):
        self.tabs[self.getActive()].start_play_thread()
        self.setButtonsState('disabled', 'Play')

    def stop (self, _=''):
        if not self.empty:
            self.tabs[self.getActive()].stop()
            self.setButtonsState('normal', 'Play')

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
            self.setButtonsState('disabled', 'Rec')

            self.recorder = Recorder(self.path, self.rec_args)
            if self.rec_args["MINIMIZE_ON_RECORD"]:
                self.root.wm_state('iconic')
            
        else:
            self.recButton.configure(relief='raised')
            self.saveRecBut['state'] = 'disabled'
            self.setButtonsState('normal', 'Rec')
            try: self.recorder.stop = True
            except: print("Couldn't stop recording - no recorder loaded :(")
            for x in self.clip_queue: self.addClip(x)

            if self.empty: self.setButtonsState('disabled', 'Empty')
            else:
                self.tabs[self.getActive()].onFocus()
                self.clip_queue = []
                self.root.update_idletasks()

    #update the amplitude scale label, and set the amp in the current recording
    def setAmp (self, text, _=''):
        db = self.ampScale.get()
        newlabel = ''
        if db < 0: newlabel = f'Amplitude: ({db} dB)'
        else: newlabel = f'Amplitude: (+{db} dB)' #db is logarithmic; should research how to add amp!
        text.config(text = newlabel)

        #update amplitude in the current frame
        self.tabs[self.getActive()].set_amp(10 ** (db/20))

    #set the amp scale to the value in the current recording; set() triggers setAmp callback
    def getAmp (self, _=''):
        dB = 20 * np.log10(self.tabs[self.getActive()].amp)
        self.ampScale.set(dB)

    def reverseSelection (self, _=''):
        self.tabs[self.getActive()].reverseSelection()

    def exportSelection (self):
        data = self.tabs[self.getActive()].saveSelection()
        name = fd.asksaveasfilename(defaultextension=".wav", filetypes=[("Wave Files", ".wav")])
        self.tabControl.tab(self.getActive(), text = name.split('/')[-1])
        print(data[0])

        with wave.open(os.path.join(self.path,name), 'wb') as wf:
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
        if self.tabs == []: self.createEmptyTab()
        else: self.tabs[self.getActive()].onFocus()

    #called on maximising; ends recording, draws newly recorded files
    def onFocus (self, _=''):
        
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
        'MINIMIZE_ON_RECORD': False,
        "USE_MESSAGE_BOXES": True,
        "MIN_AMP": -30, "MAX_AMP": 10, "AMP_RESOLUTION": 1.0
    }
    try:
        with open('data/settings.json', 'r+') as argfile:
            dat = argfile.read()
            rec_args = json.loads(dat)
            print("Keybinds loaded.")
    except:
        print('some error occured but whatevs girlie')

    binds = {'save': 'ctrl+alt+s', 'exit': 'ctrl+alt+e'}

    widnow = MainEditor(rec_args, binds, ['data/default.wav', 'data/default.wav'])
