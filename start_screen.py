"""
The starting screen where you can rebind your keys.
Made with tkinter for now, as I have some experience making functional interfaces with it.
It is kinda ugly though!
May try PyQt6 in another branch.

TODO:
 - Add option to change self.rec_args
"""

import tkinter as tk
from tkinter import ttk
from functools import partial
import main_ui as m
import settings
import keybind

import pyaudiowpatch as pyaudio #allows WASAPI
import sys
import json

class startUI:
    def __init__ (self):

        #the parameters to load the recording with
        self.rec_args = {'CHUNK': 4, 
        'FORMAT': pyaudio.paInt16,
        'RATE':48000,
        'CHANNELS': 1 if sys.platform == 'darwin' else 2,
        'RECORD_SECONDS': 10,
        'MINIMIZE_ON_RECORD': False}
        try:
            with open('data/settings.json', 'r+') as argfile:
                kb = argfile.read()
                if len(kb) == 0:
                    print("No settings file found - saving defaults.")
                    argfile.write(json.dumps(self.rec_args))
                else:
                    self.rec_args = json.loads(kb)
                    print("Keybinds loaded.")
        except:
            with open('data/settings.json', 'w') as argfile:
                print("No settings file found - saving defaults.")
                argfile.write(json.dumps(self.rec_args))

        self.loadBinds()
                
        self.root = tk.Tk()
        #self.tk.geometry("500x300")
        #self.root.geometry("400x240")#+%d+%d") % ((self.tk.winfo_screenwidth() / 2) - 380, (self.tk.winfo_screenheight() / 2) - 390))
        self.root.title("Simple Sampler")

        self.mainframe = tk.Frame(self.root,padx=5,pady=5)
        self.mainframe.pack(side='top', fill='y')
        tabControl = ttk.Notebook(self.root) 

        #create the ttk tabs for each menu option
        tab_titles = ['Info', 'Keybindings', 'Recording Settings']
        self.tabs = {}
        for title in tab_titles:
            self.tabs[title] = ttk.Frame(tabControl)
            tabControl.add(self.tabs[title], text = title) 
        tabControl.pack(expand = True, fill = "both") 

        #add regular tk frames to corresponding tab; these are the targets for each tab's GUI
        self.keybindframe = tk.Frame(self.tabs['Keybindings'], borderwidth=2,
                                     relief="sunken", padx=5, pady=5)
        self.keybindframe.pack(fill = 'both', expand = True)
        self.infoframe = tk.Frame(self.tabs['Info'], borderwidth=2,
                                  relief="sunken")
        self.infoframe.pack(fill = 'both', expand = True)
        self.recordingframe = tk.Frame(self.tabs['Recording Settings'], borderwidth=2,
                                     relief="sunken", padx=5, pady=5)
        self.recordingframe.pack(fill = 'both', expand = True)

        #create the bottom 'record' button
        sbframe = tk.Frame(self.root,padx=5,pady=5, height=30)
        sbframe.pack(side='bottom', fill='x')
        self.start_button = tk.Button(sbframe, height = 1, width = 45, bg='#11b82f', text="Start Recording!",
                                      borderwidth=2, relief="groove", activebackground='#168a2b', command=self.close)
        self.start_button.pack(fill='x')

        self.root.bind("<Return>", self.close) #quick start

        #load the UI's of each tab, draw UI
        self.loadIntroFrame()
        self.loadKeybindFrame()
        self.loadSettingsFrame()
        self.root.mainloop()

    def loadBinds (self, _=''):
        #key binds which are active in the main recorder
        self.binds = {'save': 'a', 'exit': 'ctrl+shift+esc'} #default binds
        with open('data/keybinds.json', 'r+') as keyfile:
            kb = keyfile.read()
            if len(kb) == 0:
                print("No keybind file found - saving default binds.")
                keyfile.write(json.dumps(self.binds))
            else:
                self.binds = json.loads(kb)
                print("Keybinds loaded.")

    #close this window, begin main audio sequence
    def close (self, _=''):
        if self.rebind == False:
            self.root.destroy()
            m.MainEditor(self.rec_args, self.binds)

    def loadIntroFrame (self):
        with open("data/intro-text.txt", "r+") as info:
            text = info.read()

            introLabel = tk.Label(self.infoframe, text="\nWelcome to Pillow's Simple Sample Recorder! (v0.5)\n",
                                  font='Helvetica 16 bold underline')
            introLabel.pack(side='top', fill='x')

            self.textframe = tk.Frame(self.infoframe, padx = 8, pady = 5)
            self.textframe.pack(side='top', fill='both')
            
            self.introtext = tk.Text(self.textframe, bg='#c9c9c9', font=('helvetica',10),
                                     padx = 4, pady= 2, height=11)
            self.introtext.pack(side='left', fill = 'x')
            self.introtext.insert(tk.END, text)
            self.introtext.configure(state='disabled')

            scroll = tk.Scrollbar(self.textframe, command=self.introtext.yview, bg='grey',
                                  relief='ridge', borderwidth=2)
            self.introtext.configure(yscrollcommand=scroll.set)
            scroll.pack(side="right", fill="y")

    def loadSettingsFrame (self):
        settings.SettingsWin(self.rec_args, self.recordingframe, self.updateSettings)

    def loadKeybindFrame (self):
        keybind.KeybindsWin(self.keybindframe, self.loadBinds)

    def updateSettings (self, newsettings):
        self.rec_args = newsettings

if __name__ == '__main__':
    guy = startUI()


"""
args = {'CHUNK': 4, 
        'FORMAT': pyaudio.paInt16,
        'CHANNELS': 1 if sys.platform == 'darwin' else 2,
        'RECORD_SECONDS': 10
}a
"""
