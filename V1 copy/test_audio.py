import pyttsx3

import pyaudio

p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    print(i, p.get_device_info_by_index(i)['name'])
engine = pyttsx3.init()
engine.say("Hello Sai, Jarvis is ready!")
engine.runAndWait()