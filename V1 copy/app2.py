import os
import speech_recognition as sr
import pyttsx3
from openai import OpenAI

client = OpenAI(api_key="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")


recognizer = sr.Recognizer()
tts = pyttsx3.init()

def speak(text):
    print(f"Jarvis: {text}")
    tts.say(text)
    tts.runAndWait()

def listen():
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)
        try:
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return None

def ask_ai(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",   # You can switch to gpt-3.5-turbo, gpt-4o, etc.
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant named Jarvis."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content   # ✅ new style access

def execute_command(command):
    try:
        output = os.popen(command).read()
        return output if output else "Command executed."
    except Exception as e:
        return f"Error: {e}"

def main():
    speak("Hello, I am Jarvis. You can talk or type commands.")
    while True:
        print("\nType a command or press Enter to speak:")
        user_input = input(">> ").strip()

        if not user_input:  # Use voice if no text input
            user_input = listen() or ""

        if user_input.lower() in ["exit", "quit", "bye"]:
            speak("Goodbye!")
            break

        if user_input.startswith("!"):  # Run system commands with !
            command = user_input[1:]
            result = execute_command(command)
            speak(result)
        else:
            response = ask_ai(user_input)
            speak(response)

if __name__ == "__main__":
    main()