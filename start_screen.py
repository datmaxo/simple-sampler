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
import passive_recorder as pr
import keyboard

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
        self.binds = {'save': 'a', 'exit': 'ctrl+shift+esc'} #default binds
        self.rebind = False #are we rebinding a command right now?
        with open('data/keybinds.json', 'r+') as keyfile:
            kb = keyfile.read()
            if len(kb) == 0:
                print("No keybind file found - saving default binds.")
                keyfile.write(json.dumps(self.binds))
            else:
                self.binds = json.loads(kb)
                print("Keybinds loaded.")
        
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
        self.loadRecordingFrame()
        self.root.mainloop()

    #close this window, begin main audio sequence
    def close (self, _=''):
        if self.rebind == False:
            self.root.destroy()
            pr.start_recording(self.rec_args, self.binds)

    def loadIntroFrame (self):
        with open("data/intro-text.txt", "r+") as info:
            text = info.read()

            introLabel = tk.Label(self.infoframe, text="\nWelcome to Pillow's Simple Sample Recorder! (v0.3)\n",
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

    def loadRecordingFrame (self):
        title = tk.Label(self.recordingframe, text="TODO\n",
                              font='Helvetica 12 bold underline', padx=5, pady=5, justify='right')
        title.pack(side='top', fill='x')
        note = tk.Label(self.recordingframe, text="lol this will be boring, will probs work on the editor ",
                              font='Helvetica 8', padx=5, pady=5, justify='right')
        note.pack(side='top', fill='x')

    def loadKeybindFrame (self):
        title = tk.Label(self.keybindframe, text="Keybinds\n",
                              font='Helvetica 12 bold underline', padx=5, pady=5, justify='right')
        title.pack(side='top', fill='x')
        note = tk.Label(self.keybindframe, text="NOTE: For keybinds with one or more '+' in them, all keys must be held simultaneously.",
                              font='Helvetica 8', padx=5, pady=5, justify='right')
        note.pack(side='top', fill='x')

        self.kbframe = tk.Frame(self.keybindframe, bg='#c9c9c9', relief='ridge', borderwidth=2,
                                 padx = 5, pady= 5)
        self.kbframe.pack(side='top', fill='both', expand=True)

        self.key_texts = {}
        self.key_rebind_buttons = {}
        for key in self.binds.keys():
            actionframe = tk.Frame(self.kbframe, padx=5, pady=5, relief='solid', borderwidth=2)
            actionframe.pack(side='top', anchor="nw", fill = 'x')
            
            text = tk.Label(actionframe, text=f'{key.upper()} : {self.binds[key]}')
            text.pack(side='left')
            self.key_texts[key] = text

            button = tk.Button(actionframe, text='Rebind', command=partial(self.rebindKey, key))
            button.pack(side='right')
            self.key_rebind_buttons[key] = button

            gap = tk.Frame(self.kbframe, height = 5, bg='#c9c9c9')
            gap.pack(side='top')

    def rebindKey (self, key):
        self.rebind = True
        for x in self.key_rebind_buttons.keys():
            if x != key:
                self.key_rebind_buttons[x].configure(state='disabled')
        self.start_button.configure(state='disabled')
        self.key_rebind_buttons[key].configure(text='Done?', command=partial(self.saveKeyBinding,key))
        self.key_texts[key].configure(text = f'{key.upper()} : PRESS KEY(S)')
        self.root.update_idletasks()

        keyboard.start_recording()
            
    def saveKeyBinding (self, key):
        keyseq = set([ke.name for ke in keyboard.stop_recording() if ke.event_type == "up" and ke.name != "+"])
        keyseq = sorted(list(keyseq), key=len)
        keyseq.reverse()

        if len(keyseq) > 0:
            keystr = ""
            for k in keyseq:
                keystr += k + '+'
            self.binds[key] = keystr[:-1]
            print(keystr[:-1])

            with open('data/keybinds.json', 'w+') as keyfile:
                keyfile.write(json.dumps(self.binds))
                keyfile.close() #not necessary i dont think lol

        self.key_texts[key].configure(text = f'{key.upper()} : {self.binds[key]}')
        self.key_rebind_buttons[key].configure(text='Rebind', command=partial(self.rebindKey,key))
        self.start_button.configure(state='normal')
        for x in self.key_rebind_buttons.keys():
            self.key_rebind_buttons[x].configure(state='normal')

        self.rebind=False #i don't think i need this var anymore but I'll keep it around for now

if __name__ == '__main__':
    guy = startUI()


"""
args = {'CHUNK': 4, 
        'FORMAT': pyaudio.paInt16,
        'CHANNELS': 1 if sys.platform == 'darwin' else 2,
        'RECORD_SECONDS': 10
}a
"""
