"""
I feel that it may be the silliest decision ever to use matplotlib as the core renderer of an audio editor...
but also, it works! and it doesn't even look all that horrible?
could obvs be better but for a simple editor it should do the trick :)
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

zoom_count = 1
mousex = 0
cpos = 0
start, end = [0,480000]
rect = ""

#used to round start, end positions to the nearest CHUNK value
def toNearest (num, nearest):
    return nearest * round(num / nearest)

class editorWindow ():
    def __init__ (self, file, rec_set):
        self.p = pyaudio.PyAudio()
        self.aud_data = rec_set
        self.filename = file
        self.t_signal = '' #the 'true' signal, used for playing the audio
        with wave.open(file, "r") as aud_file:
            self.channel_signal = self.readWave(aud_file)

        self.isPlaying = False #is the clip being played right now? used to control threads involved with audio.
        
        self.root = tk.Tk()
        self.root.geometry("500x300")
        self.root.title(f"Editor: {file}")

    """Using an open file, return the split-by-channel audio data, which is used to visualise the sound file."""
    def readWave (self, spf):
        # Extract Raw Audio from Wav File
        self.t_signal = spf.readframes(-1)
        self.t_signal = np.frombuffer(t_signal, np.int16)
        signal = ""

        # If Stereo, just grab every other 'chunk' of audio; remember to double these when exporting again!
        if spf.getnchannels() == 2:
            left , right = [[],[]]
            for i in range(0, len(t_signal), CHUNK * 2):
                left += list(self.t_signal[i: i + CHUNK])
                right += list(self.t_signal[i + CHUNK: i + (CHUNK * 2)])
            signal = np.array([left, right])
        elif spf.getnchannels() == 1:
            signal = np.array(t_signal)
        else:
            print("What the hell is up with the number of channels here? Can't open this, sorry dawg.")
            exit()

        return signal

    def drawWaveform (self, target):
        
        
#zoom in and out of the wave based upon the current mouse x position
#TODO: this math assumes a clip of 480000 samples; need to read length into this dawg
def scrollWave (ax, canvas, event):
    global mousex

    zoom = event.delta/120
    xmin, xmax, _, __ = plt.axis()

    #calculate distance from each side of the canvas to the mouse pointer
    dmin, dmax = [mousex - xmin, xmax - mousex]
    
    #if zoom > 0, we mult this distance by 0.25, otherwise -0.25
    dmin *= 0.25 * np.sign(zoom) * -1 
    dmax *= 0.25 * np.sign(zoom) * -1
    
    #add this distance to axis (min 0, max 480000)
    xmin = min(max(0, xmin - dmin), xmax-1)
    xmax = min(480000, xmax + dmax) #update w/ flexible length variable
        
    print([xmin, xmax])
    for a in ax:
        _, __, local_ymin, local_ymax = a.axis()
        a.axis([xmin, xmax, local_ymin, local_ymax])
    canvas.draw()

def mouse_move(event):
    global mousex
    if event.xdata != None:
        mousex = min(max(0, event.xdata), 480000)

def set_start (ax, canv, _=""):
    global mousex, start, end
    start = toNearest( int(mousex), 4 )
    if start > end: start = end - 4
    draw_play_region(ax, canv)

def set_end (ax, canv, _=""):
    global mousex, start, end
    end = toNearest( int(mousex), 4 )
    if end < start: end = start + 4
    draw_play_region(ax, canv)

def draw_play_region (ax, canv):
    global start, end, rect
    try:
        for r in rect:
            r.remove()
    except: print("No rect to remove - that's okay :)")

    print(start, end)
    rect = []
    for a in ax:
        _, __, ymin, ymax = a.axis()
        r = patches.Rectangle((start, ymin + 500), end - start, (ymax - ymin) - 1000, linewidth=1.5, edgecolor='r',
                              facecolor='none', zorder = 10)
        a.add_patch(r)
        rect.append(r)
    canv.draw()

def start_play_thread (aud, ax, canvas, _=''):
    pt = Thread(target=play_thread, args=[aud, ax, canvas])
    pt.start()

def play_thread (aud, ax, canvas, _=''):
    global start, cpos
    cpos = start * 2
    
    t1 = Thread(target=play_region, args=[aud])
    t2 = Thread(target=draw_play_pos, args=[ax,canvas])

    t1.start()
    t2.start()
    
    print("hello")
    t1.join()
    print("t1 joined")
    t2.join()
    print("t2 joined")
    
def play_region (aud, _=''):
    global start, end, cpos

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=2,
                    rate=48000,
                    output=True)

    CHUNK = 4
    for c in range(start * 2, end * 2, CHUNK):
        data = aud[c: c+CHUNK].tobytes()
        stream.write(data)
        cpos = c
    cpos = end * 2 + 1

    print('?')
    stream.close()

def draw_play_pos (ax, canvas):
    global cpos
    print("draw_play_pos started")
    
    playlines = []
    for a in ax:
        _, __, ymin, ymax = a.axis()
        p = patches.Rectangle((start, ymin + 500), 1, (ymax - ymin) - 1000, linewidth=1.5, edgecolor='black',
                              facecolor='none', zorder = 5)
        a.add_patch(p)
        playlines.append(p)
    canvas.draw()
    
    print(cpos)
    while cpos < end * 2:
        for p in playlines:
            p.set_x(cpos // 2)
        canvas.draw()
        sleep(0.05)

    for p in playlines:
        p.remove()
    canvas.draw()

if __name__ == "__main__":
    
    spf = wave.open("tmp/output(1).wav", "r")
    CHUNK = 4 

    # Extract Raw Audio from Wav File
    t_signal = spf.readframes(-1)
    t_signal = np.frombuffer(t_signal, np.int16)
    signal = ""

    # If Stereo, just grab every other 'chunk' of audio; remember to double these when exporting again!
    if spf.getnchannels() == 2:
        left , right = [[],[]]
        for i in range(0, len(t_signal), CHUNK * 2):
            left += list(t_signal[i: i + CHUNK])
            right += list(t_signal[i + CHUNK: i + (CHUNK * 2)])
        signal = np.array([left, right])
        print(signal.shape)

    root = tk.Tk()
    root.geometry("500x300")
    root.title("Gooner mansion")

    print(len(signal))
    fig, ax = plt.subplots(nrows=2, ncols=1)
    ax[0].plot(signal[0])
    ax[1].plot(signal[1])
    
    for a in ax:
        a.tick_params(
            axis='both',          # changes apply to the x-axis
            which='both',      # both major and minor ticks are affected
            bottom=False,      # ticks along the bottom edge are off
            left=False,         # ticks along the top edge are off
            labelbottom=False,   # labels along the bottom edge are off
            labelleft = False
        )
        #a.set_facecolor((143/255, 156/255, 154/255))
        #a.axis('off')
        _, __, local_ymin, local_ymax = a.axis()
        a.axis([0, len(signal[0]), local_ymin, local_ymax])
    plt.tight_layout()
    plt.connect('motion_notify_event', mouse_move)

    canvas = FigureCanvasTkAgg(fig, 
                               master = root)   
    canvas.draw() 
    canvas.get_tk_widget().pack()
    
    canvas.get_tk_widget().bind("<MouseWheel>", partial(scrollWave, ax, canvas))
    canvas.get_tk_widget().bind("<Button-1>", partial(set_start, ax, canvas))
    canvas.get_tk_widget().bind("<Button-3>", partial(set_end, ax, canvas))
    
    root.bind("<space>", partial(start_play_thread, t_signal, ax, canvas))
    root.mainloop()

