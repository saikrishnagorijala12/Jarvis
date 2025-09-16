import sys
import os
import contextlib
with open(os.devnull, 'w') as f, contextlib.redirect_stderr(f):
    import speech_recognition as sr
    import pyttsx3
# ----------------------------
# Environment setup to avoid ALSA/JACK errors
# ----------------------------
os.environ["SDL_AUDIODRIVER"] = "alsa"  # Force ALSA
os.environ["PULSE_SERVER"] = "127.0.0.1"  # Use PulseAudio

# ----------------------------
# Initialize TTS engine
# ----------------------------
tts = pyttsx3.init()


def speak(text):
    tts.say(text)
    tts.runAndWait()


# ----------------------------
# List available microphone devices
# ----------------------------
recognizer = sr.Recognizer()
mic_list = sr.Microphone.list_microphone_names()
print("Available Microphones:")
for i, name in enumerate(mic_list):
    print(f"{i}: {name}")

# ----------------------------
# Choose working microphone index
# ----------------------------
mic_index = 0  # change if needed after checking the list
try:
    with sr.Microphone(device_index=mic_index) as source:
        print("Adjusting for ambient noise, please wait...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Listening... Speak something!")
        audio = recognizer.listen(source)

    # Recognize speech
    text = recognizer.recognize_google(audio)
    print("You said:", text)
    speak(f"You said: {text}")

except sr.RequestError:
    print("Could not request results from Google Speech Recognition service.")
except sr.UnknownValueError:
    print("Google Speech Recognition could not understand audio.")
except Exception as e:
    print("Error:", e)
