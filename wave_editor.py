"""
I feel that it may be the silliest decision ever to use matplotlib as the core renderer of an audio editor...
but also, it works! and it doesn't even look all that horrible?
could obvs be better but for a simple editor it should do the trick :)

Ran into resource issues when individual editor windows are ran on their own threads.
New idea; EditorWindows are hosted via the MainEditor window on the main thread -
          passive recorder is the threaded process.

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

#used to round start, end positions to the nearest CHUNK value
def toNearest (num, nearest):
    return nearest * round(num / nearest)

class EditorWindow ():
    def __init__ (self, root, audio, rec_set):
        self.p = pyaudio.PyAudio()
        self.rec_args = rec_set #dictionary of recording arguments; used when intergacing with wave files

        if type(audio) == str:
            self.openWave(audio)
        else:
            self.t_signal = np.frombuffer(audio, np.int16) #the 'true' signal, used for playing the audio
        self.channel_signal = self.readWave()

        self.mousex = 0 #current mouse position in canvas; used for zooming
        self.start, self.end = [0, self.channel_signal.shape[1]] #where to play and stop the clip
        self.loop_rects = [] #contauns the drawn bounds of start and end points
        self.cpos = 0 #the current position in the played clip; used to render the play cursor
        self.isPlaying = False #is the clip being played right now? used to control threads involved with audio.

        #aud canvas and scroll wheel
        self.root = root
        canvFrame = tk.Frame(self.root)
        canvFrame.pack()
        self.drawWaveform(canvFrame)
        self.scroll = tk.Scrollbar(canvFrame, orient='horizontal', command=self.scrollWave)
        self.scroll.set(0,1)
        self.scroll.pack(side="bottom", fill="x")
        self.scroll.bind("<MouseWheel>", self.mousewheel_scrollWave)
        self.scroll_measures = {'units':0.05, 'pages':0.2}

    #if passed a wavefile location in __init__, open the file and read it as a numpy array
    def openWave (self, file):
        with wave.open(file, "r") as aud_file:
            self.t_signal = aud_file.readframes(-1)
            self.t_signal = np.frombuffer(self.t_signal, np.int16)
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

    """Creates the audio canvas and draws the waveform using matplotlib.
       If I implement opening waveforms from the editor, move canvas creation to __init__"""
    def drawWaveform (self, target):
        self.fig, self.ax = plt.subplots(nrows=2, ncols=1)
        self.ax[0].plot(self.channel_signal[0])
        self.ax[1].plot(self.channel_signal[1])
    
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

    #update the mouse position variable when it's over the audio canvas
    def mouse_move(self, event):
        if event.xdata != None:
            self.mousex = min(max(0, event.xdata), self.channel_signal.shape[1])

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

    #draw a funky red box between the current start and end positions
    def draw_play_region (self):
        for r in self.loop_rects:
            r.remove()

        #need to draw the box in every subplot (channel)
        self.loop_rects = []
        for a in self.ax:
            _, __, ymin, ymax = a.axis()
            r = patches.Rectangle((self.start, ymin + 250), self.end - self.start, ((ymax - 500) - (ymin + 500)),
                                  linewidth=1.5, edgecolor='r', facecolor='none', zorder = 10)
            a.add_patch(r)
            self.loop_rects.append(r)
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

        #'play audio' loop
        CHUNK = self.rec_args['CHUNK']
        for c in range(self.start * chans, self.end * chans, CHUNK):
            data = self.t_signal[c: c+CHUNK].tobytes()
            stream.write(data)
            self.cpos = c
        self.cpos = self.end * chans + 1

        stream.close()

    """ draws a scrolling cursor across the audio, following the currently played position
        uses a fair bit of CPU to move smoothy; adjust sleep time to balance performance/resources """
    def draw_play_pos (self):
        #create the cursor(s) in all channel axes
        playlines = []
        for a in self.ax:
            _, __, ymin, ymax = a.axis()
            p = patches.Rectangle((self.start, ymin + 250), 1, (ymax - ymin) - 500, linewidth=1.5,
                                  edgecolor='black', facecolor='none', zorder = 5)
            a.add_patch(p)
            playlines.append(p)
        self.canvas.draw()

        #while the clip is playing, update the cursor positioon every so often
        while self.cpos < self.end * self.rec_args['CHANNELS']:
            for p in playlines:
                p.set_x(self.cpos // self.rec_args['CHANNELS'])
            self.canvas.draw()
            sleep(0.05)

        #destroy the cursors
        for p in playlines:
            p.remove()
        self.canvas.draw()

#widnow = EditorWindow('tmp/output(1).wav', rec_args)
