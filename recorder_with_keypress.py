"""
CREATION DATE: 23/06/23
=======================
An simple implementation of the core program; passively records the last 10s of audio,
and saves it to a file when the 'a' key is pressed.
Needs a lot of tweaking to become a full app but the core works well!

Switching to PyAudioPatch and re-jigging the code a little resulted in much cleaner audio!
"""

import wave
import sys
import keyboard
from threading import Thread
import pyaudiowpatch as pyaudio #allows WASAPI

CHUNK = 4 #a value of '2' was giving poor results but any 2^n, n > 1 value works well! think small n is best
FORMAT = pyaudio.paInt16
CHANNELS = 1 if sys.platform == 'darwin' else 2
RECORD_SECONDS = 10

#rudimentary method of communicating between the two threads
#not bothering with any race condition protection but should be okay??
#while both can write, rec_thread is the only reader, and each thread can only write 0 / 1 respectfully
save = False

#the last 10 seconds of recorded audio
data = []
    
"""The main recording function; captures audio and triggers writing process when key is pressed"""
def passive_recorder (data = [], num = 0):
    global save
    p = pyaudio.PyAudio()

    #try and load WASAPI, exit if it doesn't exist (sorry Mac OS)
    default_speakers = ""
    try:
        default_speakers = p.get_default_wasapi_loopback()
    except OSError:
        spinner.print("Looks like WASAPI is not available on the system. Exiting...")
        spinner.stop()
        exit()

    RATE = int(default_speakers["defaultSampleRate"])
    print(f'c: {CHUNK}, r: {RATE}, math: { RATE / CHUNK * RECORD_SECONDS}')
    
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                    input=True, input_device_index=default_speakers["index"])

    while True:
        #record audio, only keeping the last x seconds heard
        data.append(stream.read(CHUNK))
        if len(data) > RATE / CHUNK * RECORD_SECONDS:
            data.pop(0)

        #if we've pressed 'a' and the buffer is 10s of audio
        if (save == True and len(data) == RATE / CHUNK * RECORD_SECONDS):
            #write to file in seperate thread
            print("Writing to output.wav ...")
            save = False
            name = 'tmp/output(' + str(num) + ').wav'
            write_thread = Thread(target=write_file, args=[p,data,name,RATE])
            write_thread.start()
            #no join - bad practice probably!
            print("Done!\n")
            num += 1

    #restart the recording process, using the already recorded data

""" Writing thread: makes a deep copy of the current audio buffer and then saves it to a new file.
    This setup allows for multiple clips to be saved in sequence w/ no noticable pause in recording :) """
def write_file (p, data, name, rate):
    copy = [d for d in data] #deep copy of recording so it comes out clean
    with wave.open(name, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(rate)
        for x in copy: wf.writeframes(x) #write data to wav
        wf.close()

#keyboard thread main function; listens for 'a' press
def listener():
    while True:
        keyboard.read_key()

#on 'a' press, trigger write_file in rec_thread.
def save_audio():
    global save
    save = True

#TODO: rebind this to a random key, maybe make it editable lol
keyboard.add_hotkey('a', save_audio)

rec_thread = Thread(target=passive_recorder, args=[[], 1])
rec_thread.start()
kb_thread = Thread(target=listener, args=[])
kb_thread.run()

kb_thread.join() #will run indefinitely

#unused code - can delete later?
"""
print('Recording...')
for _ in range(0, RATE // CHUNK * RECORD_SECONDS):
    #wf.writeframes(stream.read(CHUNK))
    x.append(stream.read(CHUNK))
print('Done')
print(len(x))

stream.close()
"""