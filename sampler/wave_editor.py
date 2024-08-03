"""
I feel that it may be the silliest decision ever to use matplotlib as the core renderer of an audio editor...
but also, it works! and it doesn't even look all that horrible?
could obvs be better but for a simple editor it should do the trick :)

There's been a fair bit of effort put into how this script should communicate with main_ui, but I feel like i've
completely overlooked the simplest option; passing each wave_editor the main UI instance.
Everythings works fine for now, but I'd like to go back and simplify instances where this could have made for simpler code.
"""

import tkinter as tk
from tkinter import ttk
from functools import partial
import keyboard
import pyaudiowpatch as pyaudio #allows WASAPI
import numpy as np
import sys
import wave
import io
import os
from PIL import Image
from threading import Thread
from time import sleep

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk)

#matplotlib rendering params; we don't particualrly care for accuarcy compared to performance here
mpl.rcParams['path.simplify'] = True
mpl.rcParams['path.simplify_threshold'] = 1

#operator to control whether we can store audio when frames are not in use to save time at cost to memory
clearMemOnMin = False

#used to round start, end positions to the nearest CHUNK value
def toNearest (num, nearest):
    return nearest * round(num / nearest)

class EditorWindow ():
    def __init__ (self, path, root, audio, rec_set, fig, ax, onFocusFuncs = []):
        self.path = path
        self.fig = fig
        self.ax = ax
        self.p = pyaudio.PyAudio()
        self.rec_args = rec_set #dictionary of recording arguments; used when intergacing with wave files
        self.aud_path = ''
        if type(audio) == str:
            self.aud_path = audio
        print(type(audio))

        self.t_signal = []
        if False:
            if type(audio) == str:
                self.openWave(audio)
            else:
                self.t_signal = np.frombuffer(audio, np.int16) #the 'true' signal, used for playing the audio
            self.channel_signal = self.readWave()

        self.mousex = 0 #current mouse position in canvas; used for zooming
        self.start, self.end = [0, self.rec_args['RATE'] * self.rec_args['RECORD_SECONDS']] #where to play and stop the clip
        self.loop_rects = [] #contauns the drawn bounds of start and end points
        self.cpos = 0 #the current position in the played clip; used to render the play cursor
        self.isPlaying = False #is the clip being played right now? used to control threads involved with audio.
        self.loop = False #does the clip automatically jump back to the beginning whilst playing?
        self.drawn = False #has the waveform been drawn yet?
        self.open = False #is this window currently open?
        self.saved = False #has this recording been saved at all? if not, call dialogue box on attempted closure
        self.closing = False #used to signify to the main ui that this window is being closed
        self.amp = 1.0 #extra amplitude to multiply current sample by; set by slider in main_ui
        self.loop_rects = []
        self.playlines = []
        self.onFocusFuncs = onFocusFuncs #an array of functions to call when brought into focus, just for fun :)
        
        #aud canvas and scroll wheel
        self.root = root
        self.canvFrame = tk.Frame(self.root)
        self.canvFrame.pack()
        #self.drawWaveform(canvFrame)
        self.scroll = tk.Scrollbar(self.canvFrame, orient='horizontal', command=self.scrollWave)
        self.scroll.set(0,1)
        self.scroll.pack(side="bottom", fill="x")
        self.scroll.bind("<MouseWheel>", self.mousewheel_scrollWave)
        self.scroll_measures = {'units':0.05, 'pages':0.2}

        self.root.bind("<FocusIn>", self.onFocus)
        self.root.bind("<FocusOut>", self.offFocus)

    #if passed a wavefile location in __init__, open the file and read it as a numpy array
    def openWave (self, file):
        if len(self.t_signal) < 1:
            with wave.open(os.path.join(self.path,file), "r") as aud_file:
                self.t_signal = aud_file.readframes(-1)
                self.t_signal = np.fromstring(self.t_signal, np.int16)
                self.channel_signal = self.readWave()

    #split the loaded wave file into the correct number of channels
    def readWave (self):
        signal = ""
        CHUNK = self.rec_args['CHUNK']

        # If Stereo, just grab every other 'chunk' of audio; remember to double these when exporting again!
        if self.rec_args['CHANNELS'] == 2:
            left , right = [[],[]]
            for i in range(0, len(self.t_signal), CHUNK * 2):
                left += list(self.t_signal[i: i + CHUNK])
                right += list(self.t_signal[i + CHUNK: i + (CHUNK * 2)])
            signal = np.array([left, right])
        elif self.rec_args['CHANNELS'] == 1:
            signal = np.array(t_signal)
        else:
            print("What the hell is up with the number of channels here? Can't open this, sorry dawg.")
            exit()

        return signal

    def closeWave (self):
        if clearMemOnMin:
            self.t_signal = []
            self.channel_signal = []

    """Creates the audio canvas and draws the waveform using matplotlib.
       If I implement opening waveforms from the editor, move canvas creation to __init__"""
    def drawWaveform (self, target):
        if self.open:
            
            for a in self.ax:
                for art in list(a.lines):
                    art.remove()
                    
            self.ax[0].plot(self.channel_signal[0] * self.amp, color='blue')
            self.ax[1].plot(self.channel_signal[1] * self.amp, color='blue')
            print('okay')

            if not self.drawn:
                #maybe redundant? could move to main_ui?
                for a in self.ax:
                    a.tick_params( axis='both', which='both', bottom=False, left=False,         
                                   labelbottom=False, labelleft = False )
                    #a.set_facecolor((143/255, 156/255, 154/255))
                    #a.axis('off')
                    _, __, local_ymin, local_ymax = a.axis()
                    a.axis([0, len(self.channel_signal[0]), local_ymin, local_ymax])
                
                plt.tight_layout()
                plt.connect('motion_notify_event', self.mouse_move)

                self.canvas = FigureCanvasTkAgg(self.fig, 
                                           master = target)   
                self.canvas.draw() 
                self.canvas.get_tk_widget().pack(side='top')
                self.canvas.get_tk_widget().configure(height = 250)
                
                self.canvas.get_tk_widget().bind("<MouseWheel>", self.zoomWave)
                self.canvas.get_tk_widget().bind("<Button-1>", self.set_start)
                self.canvas.get_tk_widget().bind("<Button-3>", self.set_end)
            else:
                self.canvas.draw()
                
            self.drawn = True

        self.draw_play_region()

    #scale the drawn waveform by some value (most likely amplitude but we like keeping things general here)
    #essentially just a slightly more efficient version of drawWaveform, as we don't clear the old drawings here
    #checking for if the canvas is playing (& therefore regularly updating due to draw_play_pos) keeps visuals smooth too :)
    def scaleWaveform (self, scalar):
        if self.drawn:
            i = 0
            for a in self.ax:
                for art in list(a.lines):
                    art.set_ydata(self.channel_signal[0] * scalar)
                i += 1
            if not self.isPlaying: self.canvas.draw()
        else:
            print('Canvas has not been drawn, cannot scale.')

    # update the mouse position variable when it's over the audio canvas
    def mouse_move(self, event):
        if event.xdata != None and self.open:
            self.mousex = min(max(0, event.xdata), self.channel_signal.shape[1])

    # update the specifieid settings
    # need to be able to handle speciifc settings because we don't want to change recording playback crucial ones.
    def updateSettings(self, newSettings):
        for setting in newSettings:
            self.rec_args[setting] = newSettings[setting]

    """zoom in and out of the wave based upon the current mouse x position"""
    def zoomWave (self, event):
        zoom = event.delta/120
        xmin, xmax, _, __ = self.ax[0].axis()
        length = self.channel_signal.shape[1]

        #calculate distance from each side of the canvas to the mouse pointer
        dmin, dmax = [self.mousex - xmin, xmax - self.mousex]
        
        #if zoom > 0, we mult this distance by 0.25, otherwise -0.25
        dmin *= 0.25 * np.sign(zoom) * -1 
        dmax *= 0.25 * np.sign(zoom) * -1
        
        #add this distance to axis (min 0, max 480000)
        xmin = min(max(0, xmin - dmin), xmax-1)
        xmax = min(length, xmax + dmax) #update w/ flexible length variable
            
        for a in self.ax:
            _, __, local_ymin, local_ymax = a.axis()
            a.axis([xmin, xmax, local_ymin, local_ymax])
        self.canvas.draw()

        #update scrollbar
        smin, smax = self.scroll.get()
        self.scroll.set(xmin / length, xmax / length)

    """move along the x axis of the recording, using the scroll bar below the audio canvas
       could be much more fleshed out ngl; I had no idea so much went into scrollbars !!!!"""
    def scrollWave (self, move_type='', new_pos='', jump=''):
        smin, smax = self.scroll.get()
        dist = float(new_pos) - smin #distance to move when dragging the scrollbar (standard)
        length = self.channel_signal.shape[1]

        #alternate distances moved if arrows or bg are clicked
        if move_type != 'moveto':
            dist = int(new_pos) * self.scroll_measures[jump]
            if smin + dist < 0: dist = -smin
            elif smax + dist > 1: dist = 1 - smax

        #update across all axes, and update scrollbar position so it doesn't move back!
        for a in self.ax:
            _, __, local_ymin, local_ymax = a.axis()
            a.axis([(smin + dist) * length, (smax + dist) * length, local_ymin, local_ymax])
        self.canvas.draw()
        self.scroll.set(smin + dist, smax + dist)

    #triggers scrollWave with parameters based upon mouse scroll wheel direction :)
    def mousewheel_scrollWave (self, scroll): self.scrollWave('mother', np.sign(scroll.delta), 'units')        

    #set the start position of the clip; calls draw_play_region()
    def set_start (self, _=""):
        self.start = toNearest( int(self.mousex), self.rec_args['CHUNK'] )
        if self.start >= self.end: self.start = self.end - 4
        self.draw_play_region()

    #set the end position of the clip; also calls draw_play_region()
    def set_end (self, _=""):
        self.end = toNearest( int(self.mousex), self.rec_args['CHUNK'] )
        if self.end <= self.start: self.end = self.start + 4
        self.draw_play_region()

    #set the amplitude and rescale the silly graph - might be very inefficient
    def set_amp (self, amp):
        self.amp = amp
        self.scaleWaveform(amp)

    #draw a funky red box between the current start and end positions
    def draw_play_region (self):

        #if we haven't drawn the region yet, we need to create new rectangle patches
        if len(self.loop_rects) == 0:
            for a in self.ax:
                _, __, ymin, ymax = a.axis()
                r = patches.Rectangle((self.start, ymin + 250), self.end - self.start, ((ymax - 500) - (ymin + 500)),
                                      linewidth=1.5, edgecolor='r', facecolor='r', zorder = 10, alpha=0.5)
                a.add_patch(r)
                self.loop_rects.append(r)

        #otherwise, we can simply update the position and width of the patches we already have!
        else:
            for r in self.loop_rects:
                r.set_x( self.start )
                r.set_width( self.end - self.start )

        if not self.isPlaying:
            self.canvas.draw()

    """if no audio is playing, start up the main playing process as a thread
       this needs to be done to keep the tk mainloop running smoothly."""
    def start_play_thread (self, _=''):
        if not self.isPlaying:
            self.isPlaying = True
            pt = Thread(target=self.play_thread, args=[])
            pt.start()

    #start the audio thread and the renderer thread, then wait for the clip to finish.
    def play_thread (self, _=''):
        self.cpos = self.start * 2
        
        t1 = Thread(target=self.play_region, args=[])
        t2 = Thread(target=self.draw_play_pos, args=[])

        t1.start()
        t2.start()
    
        t1.join()
        t2.join()
        
        self.cpos = 0
        self.isPlaying = False

    #plays the audio of the selected region via PyAudio
    #we mult start and end by the number of channels to convert the channel_signal position to t_signal pos
    def play_region (self, _=''):
        chans = self.rec_args['CHANNELS']
        stream = self.p.open(format=self.rec_args['FORMAT'],
                        channels=chans,
                        rate=self.rec_args['RATE'],
                        output=True)

        #'play audio' loop - can repeat if self.loop is set to true
        CHUNK = self.rec_args['CHUNK']
        play=True
        looper = self.loop
        while looper or play:
            play=False
            c = self.start * chans
            while c >= self.start * chans and c < self.end * chans:
                data = (self.t_signal[c: c+CHUNK] * self.amp).astype(type(self.t_signal[0])).tobytes()
                stream.write(data)
                self.cpos = c
                looper = self.loop
                c += CHUNK
                if not self.isPlaying:
                    print('uh oh it is time to stop the recording')
                    looper = False
                    break
        self.cpos = self.end * chans + 1

        stream.close()

    """ draws a scrolling cursor across the audio, following the currently played position
        uses a fair bit of CPU to move smoothy; adjust sleep time to balance performance/resources """
    def draw_play_pos (self):
        #create the cursor(s) in all channel axes
        self.playlines = []
        for a in self.ax:
            _, __, ymin, ymax = a.axis()
            p = patches.Rectangle((self.start, ymin + 250), 1, (ymax - ymin) - 500, linewidth=1.5,
                                  edgecolor='black', facecolor='none', zorder = 15)
            a.add_patch(p)
            self.playlines.append(p)
        self.canvas.draw()

        #while the clip is playing, update the cursor positioon every so often
        while self.cpos < self.end * self.rec_args['CHANNELS']:
            for p in self.playlines:
                p.set_x(self.cpos // self.rec_args['CHANNELS'])
            self.canvas.draw()
            sleep(0.05)

        #destroy the cursors
        self.removePlayCursor()
        self.canvas.draw()

    def removePlayCursor (self):
        for p in self.playlines:
            p.remove()
        self.playlines = []

    def saveSelection (self):
        self.saved = True
        data = self.t_signal[self.start * self.rec_args['CHANNELS'] : self.end * self.rec_args['CHANNELS']]
        return (data * self.amp).astype(type(self.t_signal[0])).tobytes()

    def stop (self):
        self.isPlaying = False
        self.removePlayCursor()

    def setLoop (self, loop):
        self.loop = loop

    #reverses the selected portion of the recording
    #currently has visual issues whilst playing, but always seemingly works fine
    def reverseSelection (self, _=''):
        clip = self.t_signal[self.start * self.rec_args['CHANNELS'] : self.end * self.rec_args['CHANNELS']]
        self.t_signal[self.start * self.rec_args['CHANNELS'] : self.end * self.rec_args['CHANNELS']] = np.flipud(clip)
        self.channel_signal = self.readWave()
        if not self.isPlaying: self.drawWaveform(self.canvFrame)

    """
    These two onFocus, offFocus funcitons were designed to help reduce memory load that comes
    with loading multiple matplotlib figures simultaneously.
    Memory leak has since been fixed, so I'm not too sure how relevant these will be once recording is properly
    implemented?
    """

    #when the editor window is brought into focus, load the waveform
    def onFocus (self, _=''):
        if not self.open:
            self.open = True
            self.openWave(self.aud_path)
            for r in self.loop_rects:
                r.set(visible = True)
            self.drawWaveform(self.canvFrame)
            for f in self.onFocusFuncs: f() #run specified funcs; for now, just used to set amplitude value in main_ui

    #when the editor window is closed, stop the track eugine!
    def offFocus (self, _=''):
        self.open = False
        self.stop()
        self.closeWave()
        for r in self.loop_rects:
            r.set(visible = False)

    #TODO - add option to ignore message boxes of all descriptions?
    def destroyEditor (self, _=''):
        kill = self.saved
        if kill:
            self.closing = True
            self.dieForReal()
        if not kill and self.rec_args['USE_MESSAGE_BOXES']:
            kill = tk.messagebox.Message(message='Recording is unsaved - do you still wish to close it?', type='yesno').show()
            print(kill)
            if kill == 'yes':
                self.closing = True
                self.dieForReal()

    #actually destroys the window
    def dieForReal (self):
        self.stop()
        #destroy loop region to prevent overlap
        try:
            for r in self.loop_rects:
                r.remove()
        except: pass
        self.root.destroy()

#widnow = EditorWindow('tmp/output(1).wav', rec_args)
