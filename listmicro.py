# import speech_recognition as sr
# for index, name in enumerate(sr.Microphone.list_microphone_names()):
#     print(f"{index}: {name}")


import sounddevice as sd
import vosk
import queue
import json

q = queue.Queue()
model = vosk.Model("vosk-model-small-en-us-0.15")

def callback(indata, frames, time, status):
    if status:
        print(status)
    q.put(bytes(indata))

def listen_vosk():
    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=callback):
        print("Listening...")
        rec = vosk.KaldiRecognizer(model, 16000)
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                print("Recognized:", result.get("text", ""))
                return result.get("text", "")
