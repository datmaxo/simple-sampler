"""
The starting screen where you can rebind your keys.
Made with tkinter for now, as I have some experience making functional interfaces with it.
It is kinda ugly though!
May try PyQt6 in another branch.

TODO:
 - Add option to rebind keys
 - Add option to change self.rec_args
 - Save options to some file (json/txt), load them on launch, save automatically altered
"""

import tkinter as tk
from functools import partial
import passive_recorder as pr

import pyaudiowpatch as pyaudio #allows WASAPI
import sys
import json

class startUI:
    def __init__ (self):

        #the parameters to load the recording with
        self.rec_args = {'CHUNK': 4, 
        'FORMAT': pyaudio.paInt16,
        'CHANNELS': 1 if sys.platform == 'darwin' else 2,
        'RECORD_SECONDS': 10}

        #key binds which are active in the main recorder
        self.binds = {'save': 'a'}
        
        self.root = tk.Tk()
        #self.tk.geometry("500x300")
        self.root.geometry("300x178")#+%d+%d") % ((self.tk.winfo_screenwidth() / 2) - 380, (self.tk.winfo_screenheight() / 2) - 390))
        self.root.title("Simple Sampler")
        
        self.mainframe = tk.Frame(self.root,padx=5,pady=5)
        self.mainframe.pack(side='top', fill='x')
        buttonframe = tk.Frame(self.mainframe)
        buttonframe.pack(side='left')
        self.infoframe = tk.Frame(self.mainframe, bg='grey', borderwidth=5,
                                  relief="ridge", width=210, height = 123)
        self.infoframe.pack(side='right')
        self.infoframe.pack_propagate(False) 
        self.targframe = tk.Frame(self.infoframe)
        
        #x = tk.Label(self.infoframe, text='test')
        #x.pack()
    
        self.info_but = tk.Button(buttonframe, height = 2, width =5, text="Info", padx= 16, command=self.loadIntroFrame)
        self.info_but.pack()

        self.rec_set_but = tk.Button(buttonframe, height = 2, width =5, text="Recording\nSettings", padx= 16, command=self.close)
        self.rec_set_but.pack()

        self.key_set_but = tk.Button(buttonframe, height = 2, width =5, text="Key\nBindings", padx= 16, command=self.close)
        self.key_set_but.pack()

        #button width seems to be 2.5x the root geometry
        sbframe = tk.Frame(self.root,padx=5,pady=5)
        sbframe.pack(side='bottom')
        self.start_button = tk.Button(sbframe, height = 1, width = 45, bg='#11b82f', text="Start Recording!",
                                      borderwidth=2, relief="groove", activebackground='#168a2b', command=self.close)
        self.start_button.pack(side='bottom')

        self.loadIntroFrame()
        self.root.mainloop()

    def close (self):
        self.root.destroy()
        pr.start_recording(self.rec_args, self.binds)

    def loadIntroFrame (self):
        try: self.targframe.destroy()
        except: print("'targframe' not instantiated; cannot be destroyed.")
        with open("data/intro-text.txt", "r+") as info:
            text = info.read()

            self.targframe = tk.Frame(self.infoframe)
            self.targframe.pack()
            self.introtext = tk.Text(self.targframe, bg='grey', font=('arial',10),
                                     padx = 4, pady= 2)
            self.introtext.pack()
            self.introtext.insert(tk.END, text)

if __name__ == '__main__':
    guy = startUI()


"""
args = {'CHUNK': 4, 
        'FORMAT': pyaudio.paInt16,
        'CHANNELS': 1 if sys.platform == 'darwin' else 2,
        'RECORD_SECONDS': 10
}a
"""
