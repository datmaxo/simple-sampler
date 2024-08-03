"""
CREATION DATE: 23/06/23
=======================
An simple implementation of the core program; passively records the last 10s of audio,
and saves it to a file when the 'a' key is pressed.
Switching to PyAudioPatch and re-jigging the code a little resulted in much cleaner audio!

"""

import wave
import sys
import os
import keyboard
from threading import Thread
import pyaudiowpatch as pyaudio #allows WASAPI
import sampler.wave_editor

class Recorder:
    def __init__ (self, path, rec_args):
        self.path = path
        self.p = pyaudio.PyAudio()
        self.rec_args = rec_args
        self.data = []
        
        self.save = False
        self.stop = False
        self.max_size = self.rec_args['RATE'] / self.rec_args['CHUNK'] * self.rec_args['RECORD_SECONDS']

        recThread = Thread(target = self.start_recording, args=[])
        keyThread = Thread(target = self.listener, args=[])
        recThread.start()
        keyThread.start()

    def listener(self):
        while not self.stop:
            keyboard.read_key()
    
    """The main recording function; captures audio and triggers writing process when key is pressed"""
    def start_recording (self):
        p = pyaudio.PyAudio()
        printed_note = False

        #try and load WASAPI, exit if it doesn't exist (sorry Mac OS)
        default_speakers = ""
        try:
            default_speakers = p.get_default_wasapi_loopback()
        except OSError:
            print("Looks like WASAPI is not available on the system. Exiting...")
            exit()

        self.rec_args['RATE'] = int(default_speakers["defaultSampleRate"])
        print(f"""c: {self.rec_args['CHUNK']}, r: {self.rec_args['RATE']},math: {self.max_size}""")
        
        stream = p.open(format= self.rec_args['FORMAT'],
                        channels= self.rec_args['CHANNELS'],
                        rate= self.rec_args['RATE'],
                        input=True,
                        input_device_index=default_speakers["index"])

        while not self.stop:
            #record audio, only keeping the last x seconds heard
            self.data.append(stream.read(self.rec_args['CHUNK']))
            if len(self.data) > self.max_size:
                self.data.pop(0)

        self.data = []

    #this used to be a subprocess - is now called by MainEditor on the main thread :)
    def write_file (self, num):
        if len(self.data) == self.max_size:
            copy = [d for d in self.data] #deep copy of recording so it comes out clean
            filename = f'tmp/output ({num}).wav'
            with wave.open(os.path.join(self.path,filename), 'wb') as wf:
                wf.setnchannels(self.rec_args['CHANNELS'])
                wf.setsampwidth(self.p.get_sample_size(self.rec_args['FORMAT']))
                wf.setframerate(self.rec_args['RATE'])
                for x in copy: wf.writeframes(x) #write data to wav
                wf.close()
            return filename
        return None
        

#keyboard thread main function; listens for 'a' press
def listener():
    global stop
    while not stop:
        keyboard.read_key()

#on 'a' press, trigger write_file in rec_thread.
def save_audio():
    global save
    save = True

def kill_process():
    global stop
    stop = True

#the function which triggers the recording process from the UI script
def start_recording(rec_args, binds):
    keyboard.add_hotkey(binds['save'], save_audio)
    keyboard.add_hotkey(binds['exit'], kill_process)

    rec_thread = Thread(target=passive_recorder, args=[[], rec_args, 1])
    rec_thread.start()
    kb_thread = Thread(target=listener, args=[])
    kb_thread.start()

    #will run until kill_process is called
    kb_thread.join()
    rec_thread.join()
    print('lol cya')
    exit()


#I don't think there's a way to run this standalone anymore, R.I.P
"""
if __name__ == "__main__":

    rec_args = {'CHUNK': 4, 
        'FORMAT': pyaudio.paInt16,
        'CHANNELS': 1 if sys.platform == 'darwin' else 2,
        'RECORD_SECONDS': 10
    }
    
    #TODO: rebind this to a random key, maybe make it editable lol
    keyboard.add_hotkey('a', save_audio)

    rec_thread = Thread(target=passive_recorder, args=[[], rec_args, 1])
    rec_thread.start()
    kb_thread = Thread(target=listener, args=[])
    kb_thread.run()

    kb_thread.join() #will run indefinitely
"""
