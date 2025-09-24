import pyttsx3

engine = pyttsx3.init()
voices = engine.getProperty('voices')

for i, voice in enumerate(voices):
    print(f"Voice {i}: {voice.name} ({voice.id})")


from TTS.api import TTS

# Load a pretrained female English voice
tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False, gpu=False)

# Generate audio to a file
tts.tts_to_file(text="Hello Sai, I am Friday with a natural female voice.", file_path="output.wav")
