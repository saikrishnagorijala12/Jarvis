import os
import datetime
import speech_recognition as sr
import pyttsx3
import spacy
import wikipedia
import pyjokes
import ollama  # <-- Ollama for llama3.1

# ------------------ Initialize ------------------
nlp = spacy.load("en_core_web_sm")
recognizer = sr.Recognizer()
tts = pyttsx3.init()
tts.setProperty('rate', 160)
tts.setProperty('volume', 1.0)

WAKE_WORDS = ["jarvis", "hey jarvis"]
conversation = []  # memory for llama3.1

# ------------------ Speak ------------------
def speak(text):
    print(f"Jarvis: {text}")
    tts.say(text)
    tts.runAndWait()

# ------------------ Listen ------------------
def listen(timeout=None):
    with sr.Microphone(device_index=0) as source:
        if timeout:
            print(f"Listening for {timeout} seconds...")
        else:
            print("Listening...")
        try:
            audio = recognizer.listen(source, timeout=timeout)
            return recognizer.recognize_google(audio).lower()
            print(recognizer.recognize_google(audio).lower())
        except sr.UnknownValueError:
            return "Listen not working"
        except sr.RequestError:
            speak("Speech service unavailable.")
            return ""
        except sr.WaitTimeoutError:
            return ""

# ------------------ Preprocess ------------------
def preprocess(text):
    doc = nlp(text.lower())
    return [token.lemma_ for token in doc if token.is_alpha and not token.is_stop]

# ------------------ Intents ------------------
intents = {
    "greeting": ["hello", "hi", "hey", "morning"],
    "exit": ["bye", "quit", "exit"],
    "weather": ["weather", "forecast", "temperature"],
    "time": ["time", "clock"],
    "date": ["date", "day", "today"],
    "system_command": ["open", "launch", "shutdown", "restart"],
    "wikipedia": ["wikipedia", "who", "what", "tell me about"],
    "search": ["search", "google", "look up", "find"],
    "joke": ["joke", "funny", "laugh"],
}

# ------------------ Intent Classifier ------------------
def classify_intent(text):
    tokens = preprocess(text)
    for intent, keywords in intents.items():
        if any(word in tokens for word in keywords):
            return intent
    return "unknown"

# ------------------ Wikipedia ------------------
def handle_wikipedia(text):
    try:
        query = text
        for kw in ["wikipedia", "who", "what", "tell me about"]:
            query = query.replace(kw, "")
        query = query.strip()
        if not query:
            return "What do you want me to search on Wikipedia?"
        return wikipedia.summary(query, sentences=2)
    except:
        return "I couldn't find anything on Wikipedia."

# ------------------ LLaMA 3.1 Search ------------------
def handle_search(text):
    query = text
    for kw in ["search", "google", "look up", "find"]:
        query = query.replace(kw, "")
    query = query.strip()
    if not query:
        return "What should I search for?"

    try:
        conversation.append({"role": "user", "content": f"Search for: {query}"})
        response = ollama.chat(
            model="llama3.1",
            messages=conversation
        )
        reply = response["message"]["content"]
        conversation.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"Search failed: {e}"

# ------------------ System Commands ------------------
def handle_system(text):
    text_lower = text.lower()
    if "chrome" in text_lower:
        os.system("google-chrome &")
        return "Opening Chrome"
    elif "shutdown" in text_lower:
        os.system("shutdown now")
        return "Shutting down system"
    elif "restart" in text_lower:
        os.system("reboot")
        return "Restarting system"
    else:
        return "System command not recognized."

# ------------------ Intent Router ------------------
def handle_intent(intent, text):
    if intent == "greeting":
        return "Hello! How can I help you?"
    elif intent == "exit":
        return "Goodbye!"
    elif intent == "weather":
        return "Weather feature not implemented yet."
    elif intent == "time":
        return f"The time is {datetime.datetime.now().strftime('%H:%M:%S')}"
    elif intent == "date":
        return f"Today's date is {datetime.date.today().strftime('%B %d, %Y')}"
    elif intent == "system_command":
        return handle_system(text)
    elif intent == "wikipedia":
        return handle_wikipedia(text)
    elif intent == "search":
        return handle_search(text)
    elif intent == "joke":
        return pyjokes.get_joke()
    else:
        # fallback → ask llama3.1
        try:
            conversation.append({"role": "user", "content": text})
            response = ollama.chat(
                model="llama3.1",
                messages=conversation
            )
            reply = response["message"]["content"]
            conversation.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            return f"I couldn’t process that: {e}"

# ------------------ Wake Word ------------------
def listen_for_wake_word():
    while True:
        text = listen(timeout=3)
        if any(w in text for w in WAKE_WORDS):
            speak("Yes, I am listening. What can I do for you?")
            return True

# ------------------ Main Loop ------------------
def main():
    speak("Jarvis is online. Say 'Jarvis' to wake me up.")
    while True:
        if listen_for_wake_word():
            while True:
                user_input = listen()
                if not user_input:
                    continue
                if user_input in ["exit", "quit", "bye"]:
                    speak("Goodbye!")
                    return
                response = handle_intent(classify_intent(user_input), user_input)
                speak(response)

if __name__ == "__main__":
    main()
