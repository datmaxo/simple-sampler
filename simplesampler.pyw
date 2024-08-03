from sampler import start_screen
import sys
import os

if __name__ == '__main__':

    try:
        path = sys._MEIPASS
    except:
        path = os.path.dirname(start_screen.__file__)
    print(path)
    start_screen.startUI(path)
