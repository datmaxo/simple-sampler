"""
Settings window; drawn in both the start screen and editor windows, so I figured it'd be best to put it in its
own module!
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
def __testsavefunc (dat=''): print(dat)

class SettingsWin:
    def __init__ (self, args, root="", savefunc = ''):

        #establish root - if no parent window defined, create base tk root
        self.root = root
        if root == '':
            self.root = tk.Tk()
            self.root.title("Settings")
            self.root.geometry("500x300")

        self.args = args
        self.savefunc = savefunc
        self.loadMain()

        #if no parent window, run mainloop
        if root == '':
            self.root.mainloop()

    def loadMain (self):
        baseframe = tk.Frame(self.root, padx=5, pady=5)
        baseframe.pack()
        
        title = tk.Label(baseframe, text="Settings",
                              font='Helvetica 12 bold underline', padx=5, pady=5, justify='right')
        title.pack(side='top', fill='x')
        note = tk.Label(baseframe, text="NOTE: all settings are presented with their internal names, and may be ambiguous.\nFEW SAFETY CHECKS ARE MADE; ALTERATIONS MAY LEAD TO ERRONEOUS BEHAVIOUR.",
                              font='Helvetica 8', padx=5, pady=5, justify='center')
        note.pack(side='top', fill='x')

        scrollZone = tk.Frame(baseframe, bd=2, relief='ridge')
        scrollZone.pack(side='top', fill='x')

        self.setframe = tk.Canvas(scrollZone, bg='#c9c9c9', highlightthickness=0)
        self.setframe.pack(side='left', fill='x', expand=True)
        scroll = tk.Scrollbar(scrollZone, command=self.setframe.yview, bg='grey', relief='ridge', borderwidth=2)
        scroll.pack(side='right', fill='y')

        self.settings_inputs = {}
        i = 10
        for key in self.args.keys():
            actionframe = tk.Frame(self.setframe, bg='#c9c9c9')
            
            text = tk.Label(actionframe, text=f'{key.upper()} :',  bg='#c9c9c9')
            text.pack(side='left')
            e = "" #the object to be added to the settings dict; must have a get() method

            #if the setting is a boolean, we create a checkbox (where e is an intvar), otherwise it's a normal entry
            if type(self.args[key]) == bool:
                e = tk.IntVar()
                e.set(int(self.args[key]))
                b = tk.Checkbutton(actionframe, variable=e, bg='#c9c9c9', activebackground='#c9c9c9')
                b.pack(side='left')
                #if bool(self.args[key]): b.select()
            else:
                e = tk.Entry(actionframe, width=20)
                e.pack(side='left')
                e.insert(0, self.args[key])
            self.settings_inputs[key] = e

            self.setframe.create_window(10,i,window=actionframe, anchor='nw')
            i+=25

        self.setframe.configure(yscrollcommand=scroll.set, height=150, scrollregion=(0,0,0,(len(self.args) + 1) * 25))

        bgap = tk.Frame(baseframe, height = 5)
        bgap.pack(side='top')
        saveButton = tk.Button(baseframe, text='Save Settings', command=partial(self.saveSettings, self.settings_inputs))
        saveButton.pack(side='bottom', fill='x')

    def saveSettings (self, inputs):
        #get the new settings, saving them only if they are of a compatable type with the previous setting value
        new_args = {}
        for k in inputs.keys():
            val = inputs[k].get()
            print(val)
            try:
                if type(self.args[k]) == str: val = str(val) #pointless 
                elif type(self.args[k]) == int: val = int(val)
                elif type(self.args[k]) == float: val = float(val)
                elif type(self.args[k]) == bool: val = bool(val)
                else: val = self.args[k] #in the event of no args, just be default
            except: val = self.args[k]
            new_args[k] = val

            #clear the setting and replace with the true new value - in practice, this resets vals of the wrong type
            if type(val) != bool:
                inputs[k].delete(0,999999)
                inputs[k].insert(0, val)

        #write to settings json
        self.args = new_args
        print(self.args)
        with open('data/settings.json', 'w+') as argfile:
            argfile.write(json.dumps(self.args))

        #execute savefunc to send changes to main module object        
        type_func = lambda: print('test') #generic function to test type against; kind of pointless but whatever
        if type(self.savefunc) == type(type_func) or str(type(self.savefunc)) == "<class 'method'>":
            print('Valid savefunc: executing now...')
            try:
                self.savefunc(new_args)
            except Exception as e:
                print(e)
        else:
            print(f'this is weird? type: {type(self.savefunc)}')

# if executed standalone, create settings window with a few default options
if __name__ == '__main__':
    rec_args = {'CHUNK': 4, 
                'FORMAT': pyaudio.paInt16,
                'RATE':48000,
                'CHANNELS': 1 if sys.platform == 'darwin' else 2,
                'RECORD_SECONDS': 10,
                'MINIMIZE_ON_RECORD': False,
                'USE_MESSAGE_BOXES': False}

    s = SettingsWin(rec_args, '', __testsavefunc)
