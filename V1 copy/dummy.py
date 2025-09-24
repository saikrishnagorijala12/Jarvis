import sounddevice as sd
import vosk, sys, queue, json
import numpy as np
import scipy.signal

q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(indata.copy())

model = vosk.Model("model")
recognizer = vosk.KaldiRecognizer(model, 16000)

# Pick mic device (your built-in mic is index 0)
device_info = sd.query_devices(0, 'input')
samplerate = int(device_info['default_samplerate'])
print(f"Using device 0 at {samplerate} Hz, resampling to 16000 Hz")

with sd.InputStream(samplerate=samplerate, blocksize=8000,
                    dtype='float32', channels=1, device=0, callback=callback):
    print("Say something (Ctrl+C to stop):")
    while True:
        data = q.get()
        # Resample from hardware rate (e.g. 44100) to 16000
        resampled = scipy.signal.resample_poly(data[:, 0], 16000, samplerate)
        resampled = (resampled * 32767).astype(np.int16).tobytes()

        if recognizer.AcceptWaveform(resampled):
            result = json.loads(recognizer.Result())
            print("You said:", result.get("text", ""))
        else:
            partial = json.loads(recognizer.PartialResult())
            if partial.get("partial"):
                print("Partial:", partial["partial"])
