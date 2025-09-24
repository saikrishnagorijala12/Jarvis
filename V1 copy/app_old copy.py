import os
import datetime
import speech_recognition as sr
import pyttsx3
import spacy
import subprocess
import wikipedia
import webbrowser
import requests
import pyjokes
import random
from textblob import TextBlob

# ------------------ Initialize ------------------
nlp = spacy.load("en_core_web_sm")
recognizer = sr.Recognizer()
tts = pyttsx3.init()
tts.setProperty('rate', 160)
tts.setProperty('volume', 1.0)

WAKE_WORDS = ["jarvis", "hey jarvis"]
reminders = []
current_mood = "serious"

# ------------------ Voice Setup ------------------
def setup_voices():
    voices = tts.getProperty("voices")
    print("\n=== Available Voices ===")
    for i, v in enumerate(voices):
        print(f"{i}: {v.id} ({v.name})")

    voice_map = {}
    if len(voices) >= 4:
        voice_map["serious"] = voices[0].id
        voice_map["funny"] = voices[1].id
        voice_map["sarcastic"] = voices[2].id
        voice_map["empathetic"] = voices[3].id
    else:
        for mood in ["serious", "funny", "sarcastic", "empathetic"]:
            voice_map[mood] = voices[0].id if voices else None

    return voice_map

voice_map = setup_voices()

# ------------------ Sentiment Detection ------------------
def detect_sentiment(user_input):
    blob = TextBlob(user_input)
    if blob.sentiment.polarity > 0.3:
        return "positive"
    elif blob.sentiment.polarity < -0.3:
        return "negative"
    else:
        return "neutral"

# ------------------ Speak Function ------------------
def speak(text, user_input=""):
    global current_mood
    sentiment = detect_sentiment(user_input) if user_input else "neutral"

    # Hybrid auto empathy: switch mood when user is sad/negative
    if sentiment == "negative" and current_mood != "empathetic":
        current_mood = "empathetic"

    rate, volume = 160, 1.0
    if current_mood == "funny": rate = 190
    elif current_mood == "sarcastic": rate = 150
    elif current_mood == "empathetic": rate = 140; volume = 0.8

    if sentiment == "positive": rate += 15
    elif sentiment == "negative": rate -= 15; volume = 0.7

    if current_mood in voice_map and voice_map[current_mood]:
        tts.setProperty("voice", voice_map[current_mood])
    tts.setProperty("rate", rate)
    tts.setProperty("volume", volume)

    print(f"Jarvis ({current_mood}/{sentiment}): {text}")
    tts.say(text)
    tts.runAndWait()

# ------------------ Listen ------------------
def listen(timeout=None, phrase_time_limit=5):
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print("Listening...")
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            result = recognizer.recognize_google(audio).lower()
            print(f"Raw recognition result: '{result}'")
            return result
        except:
            return ""

# ------------------ Intents ------------------
intents = {
    "greeting": ["hello", "hi", "hey"],
    "exit": ["bye", "quit", "exit"],
    "emotions": ["sad", "happy", "tired", "angry", "upset", "excited", "feel", "feeling"],
    "time": ["time", "clock"],
    "date": ["date", "day", "today"],
    "system_command": ["open", "launch", "shutdown", "restart"],
    "wikipedia": ["wikipedia", "who", "what"],
    "search": ["search", "google", "look up", "find"],
    "fun": ["joke", "trivia", "question"],
    "mood": ["serious", "funny", "sarcastic", "empathetic"],
}

def preprocess(text):
    doc = nlp(text.lower())
    return [token.lemma_ for token in doc if token.is_alpha and not token.is_stop]

def classify_intent(text):
    tokens = preprocess(text)
    for intent, keywords in intents.items():
        if any(word in tokens for word in keywords):
            return intent
    return "unknown"

# ------------------ Handlers ------------------
def handle_emotion(text):
    if "happy" in text: return "That’s wonderful! I’m glad to hear that. Keep smiling!"
    elif "sad" in text or "tired" in text: return "I’m sorry you’re feeling this way. Want me to cheer you up with a joke?"
    elif "angry" in text: return "I can sense your frustration. Want me to play some calming music?"
    else: return "I hear you. It's okay to feel that way. I'm here for you."

def handle_wikipedia(text):
    try:
        query = text.replace("wikipedia", "").strip()
        return wikipedia.summary(query, sentences=2)
    except: return "I couldn't find anything on Wikipedia."

def handle_search(text):
    query = text.replace("search", "").replace("google", "").strip()
    if not query: return "What should I search for?"
    try:
        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)
        return f"Here are some results for {query}."
    except: return "Search failed."

def handle_fun(text):
    if "joke" in text:
        return pyjokes.get_joke()
    return "Try asking for a joke or trivia!"

def set_mood(mood):
    global current_mood
    current_mood = mood
    return f"My personality is now {mood}."

# ------------------ Intent Router ------------------
def handle_intent(intent, text):
    if intent == "greeting": return "Hello! How can I help you?"
    elif intent == "exit": return "Goodbye!"
    elif intent == "time": return f"The time is {datetime.datetime.now().strftime('%H:%M:%S')}"
    elif intent == "date": return f"Today is {datetime.date.today().strftime('%B %d, %Y')}"
    elif intent == "emotions": return handle_emotion(text)
    elif intent == "wikipedia": return handle_wikipedia(text)
    elif intent == "search": return handle_search(text)
    elif intent == "fun": return handle_fun(text)
    elif intent == "mood":
        if "funny" in text: return set_mood("funny")
        elif "sarcastic" in text: return set_mood("sarcastic")
        elif "empathetic" in text: return set_mood("empathetic")
        else: return set_mood("serious")
    return "Hmm, I didn't understand that."

# ------------------ Wake Word ------------------
def listen_for_wake_word():
    while True:
        text = listen(timeout=3)
        if any(w in text for w in WAKE_WORDS):
            speak("Yes, I’m listening.")
            return True

# ------------------ Main ------------------
def main():
    speak("Jarvis is online. Say 'Jarvis' to wake me up.")
    while True:
        if listen_for_wake_word():
            while True:
                user_input = listen()
                if not user_input: continue
                if user_input in ["exit", "quit", "bye"]:
                    speak("Goodbye!")
                    return
                response = handle_intent(classify_intent(user_input), user_input)
                speak(response, user_input)

if __name__ == "__main__":
    main()
