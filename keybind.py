"""
Keybinds window, moved to its own module because then I can draw it more dynamically :)
"""

#TODO: add 'reset to default settings' option
#TODO: add scroll wheel to settings frame - allow for scrolling if more settings are added

import tkinter as tk
from functools import partial
import pyaudiowpatch as pyaudio #allows WASAPI
import sys
import json

#a test funciton to pass as savefunc into SettingsWin
#savefunc is called upon saving the settings in order to update them within the main module object
def __testsavefunc (): print('Keybinds loaded?')

class KeybindsWin:
    def __init__ (self, root="", savefunc = ''):

        #key binds which are active in the main recorder
        self.binds = {'save': 'a', 'exit': 'ctrl+shift+esc'} #default binds
        self.rooted = not (root == '')
        with open('data/keybinds.json', 'r+') as keyfile:
            kb = keyfile.read()
            if len(kb) == 0:
                print("No keybind file found - saving default binds.")
                keyfile.write(json.dumps(self.binds))
            else:
                self.binds = json.loads(kb)
                print("Keybinds loaded.")

        #establish root - if no parent window defined, create base tk root
        self.root = root
        if not self.rooted:
            self.root = tk.Tk()
            self.root.title("Settings")
            self.root.geometry("500x300")
            self.root.protocol("WM_DELETE_WINDOW", self.onClose)

        self.savefunc = savefunc
        self.loadMain()

        #if no parent window, run mainloop
        if not self.rooted:
            self.root.mainloop()

    def loadMain (self):
        baseframe = tk.Frame(self.root, padx=5, pady=5)
        baseframe.pack()
        
        title = tk.Label(baseframe, text="Keybinds\n",
                              font='Helvetica 12 bold underline', padx=5, pady=5, justify='right')
        title.pack(side='top', fill='x')
        note = tk.Label(baseframe, text="NOTE: For keybinds with one or more '+' in them, all keys must be held simultaneously.",
                              font='Helvetica 8', padx=5, pady=5, justify='right')
        note.pack(side='top', fill='x')

        self.kbframe = tk.Frame(baseframe, bg='#c9c9c9', relief='ridge', borderwidth=2,
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

        #if not within the main window, we need some way to send the bound keys to main
        if not self.rooted:
            bgap = tk.Frame(baseframe, height = 5)
            bgap.pack(side='top')
            saveButton = tk.Button(baseframe, text='Save Keybinds', command=self.saveSettings)
            saveButton.pack(side='bottom', fill='x')

    def rebindKey (self, key):
        self.rebind = True
        for x in self.key_rebind_buttons.keys():
            if x != key:
                self.key_rebind_buttons[x].configure(state='disabled')
        if not self.rooted: self.saveButton.configure(state='disabled')
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
        if not self.rooted: self.saveButton.configure(state='normal')
        for x in self.key_rebind_buttons.keys():
            self.key_rebind_buttons[x].configure(state='normal')

    def saveSettings (self):
        #just execute the save func, get main to reload keybinds      
        type_func = lambda: print('test') #generic function to test type against; kind of pointless but whatever
        if type(self.savefunc) == type(type_func) or str(type(self.savefunc)) == "<class 'method'>":
            print('Valid savefunc: executing now...')
            try:
                self.savefunc()
            except:
                print('Some type of error occured or something, to be honest I do not care and will be promptly going on holiday.')
        else:
            print(f'this is weird? type: {type(self.savefunc)}')

    def onClose (self):
        self.saveSettings()
        self.root.destroy()

# if executed standalone, create settings window with a few default options
if __name__ == '__main__':

    s = KeybindsWin('', __testsavefunc)
