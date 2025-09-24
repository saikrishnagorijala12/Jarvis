import os
import datetime
import speech_recognition as sr
import pyttsx3
import spacy
import subprocess
import wikipedia
from googlesearch import search
import webbrowser
import requests
from bs4 import BeautifulSoup
import pyjokes

# ------------------ Initialize ------------------
nlp = spacy.load("en_core_web_sm")
recognizer = sr.Recognizer()
tts = pyttsx3.init()
tts.setProperty('rate', 160)
tts.setProperty('volume', 1.0)
WAKE_WORDS = ["jarvis", "hey jarvis"]
reminders = []

# ------------------ Speak Function ------------------
def speak(text):
    print(f"Jarvis: {text}")
    tts.say(text)
    tts.runAndWait()

# ------------------ Listen Function ------------------
def listen(timeout=None):
    with sr.Microphone() as source:
        if timeout:
            print(f"Listening for {timeout} seconds...")
        else:
            print("Listening...")
        try:
            audio = recognizer.listen(source, timeout=timeout)
            # print("KeyWord : "+recognizer.recognize_google(audio).lower())
            return recognizer.recognize_google(audio).lower()
        except sr.UnknownValueError:
            return ""
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
    "greet_friend" :['friend'],
    "weather": ["weather", "forecast", "temperature"],
    "time": ["time", "clock"],
    "date": ["date", "day", "today"],
    "system_command": ["open", "launch", "run", "shutdown", "restart", "volume", "brightness", "ip"],
    "file": ["file", "folder", "directory", "create", "delete", "list"],
    "wikipedia": ["wikipedia", "who", "what", "tell me about"],
    "search": ["search", "google", "look up", "find"],
    "joke": ["joke", "funny", "laugh"],
    "sleep": ["sleep", "standby"],
    "reminder" : ["remind", "reminder", "note"],
}

# ------------------ Intent Classifier ------------------
def classify_intent(text):
    tokens = preprocess(text)
    greeting_words = intents.get("greeting", [])


    if any(word in tokens for word in greeting_words):
        doc = nlp(text)
        if any(ent.label_ == "PERSON" for ent in doc.ents):
            return "greet_friend"
        return "greeting"


    for intent, keywords in intents.items():
        if any(word in tokens for word in keywords):
            return intent
    return "unknown"

# ------------------ System Commands ------------------
def handle_system(text):
    text_lower = text.lower()
    if "firefox" in text_lower:
        os.system("firefox &")
        return "Opening Firefox"
    elif "chrome" in text_lower:
        os.system("google-chrome &")
        return "Opening Chrome"
    elif "code" in text_lower or "vs code" in text_lower:
        os.system("code &")
        return "Opening VS Code"
    elif "terminal" in text_lower:
        os.system("gnome-terminal &")
        return "Opening Terminal"
    elif "shutdown" in text_lower:
        os.system("shutdown now")
        return "Shutting down system"
    elif "restart" in text_lower:
        os.system("reboot")
        return "Restarting system"
    elif "volume up" in text_lower:
        os.system("pactl set-sink-volume @DEFAULT_SINK@ +10%")
        return "Volume increased"
    elif "volume down" in text_lower:
        os.system("pactl set-sink-volume @DEFAULT_SINK@ -10%")
        return "Volume decreased"
    elif "ip" in text_lower:
        ip = subprocess.getoutput("hostname -I | awk '{print $1}'")
        return f"Your IP address is {ip}"
    elif "system info" in text_lower:
        info = subprocess.getoutput("neofetch --stdout")
        return info
    else:
        return "System command not recognized."

# ------------------ File Commands ------------------
def handle_file(text):
    text_lower = text.lower()
    if "list" in text_lower:
        files = os.listdir(".")
        return "Files: " + ", ".join(files)
    elif "create folder" in text_lower:
        os.makedirs("NewFolder", exist_ok=True)
        return "Folder 'NewFolder' created"
    elif "delete folder" in text_lower:
        if os.path.exists("NewFolder"):
            os.rmdir("NewFolder")
            return "Folder 'NewFolder' deleted"
        else:
            return "Folder 'NewFolder' does not exist"
    elif "open folder" in text_lower:
        os.system("xdg-open . &")
        return "Opening current folder"
    else:
        return "File command not recognized."

# ------------------ Wikipedia Lookup ------------------
def handle_wikipedia(text):
    try:
        query = text
        for kw in ["wikipedia", "who", "what", "tell me about"]:
            query = query.replace(kw, "")
        query = query.strip()
        if not query:
            return "What do you want me to search on Wikipedia?"
        result = wikipedia.summary(query, sentences=2)
        return result
    except:
        return "I couldn't find anything on Wikipedia."

# ------------------ Reminders Lookup ------------------
def set_reminder():
    speak("What should I remind you about?")
    task = listen(timeout=10)
    if not task:
        speak("I didn't catch that. Please try again later.")
        return "Reminder not set."

    speak("When should I remind you? Please say in minutes from now.")
    time_input = listen(timeout=10)

    try:
        minutes = int(time_input)
        remind_time = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        reminders.append((remind_time, task))
        return f"Reminder set for {minutes} minutes from now: {task}"
    except ValueError:
        return "Could not understand the time. Reminder not set."

def check_reminders():
    now = datetime.datetime.now()
    for r in reminders[:]:
        remind_time, task = r
        if now >= remind_time:
            speak(f"Reminder: {task}")
            reminders.remove(r)


# ------------------ Weather Friend ------------------
def ask_city():
    speak("Which city would you like the weather for?")
    city = listen(timeout=5)
    if not city:
        speak("I didn't catch that. Using default city Guntur.")
        city = "Guntur"
    return city

def get_weather(city):
    api_key = "431a1f97c7bb066efa54bbc925a4a715"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        res = requests.get(url, timeout=5).json()
        if res.get("cod") != 200:
            return f"Could not get weather for {city}."
        desc = res['weather'][0]['description']
        temp = res['main']['temp']
        feels = res['main']['feels_like']
        humidity = res['main']['humidity']
        return f"Weather in {city}: {desc}, temperature {temp}°C, feels like {feels}°C, humidity {humidity}%."
    except Exception as e:
        return f"Error fetching weather: {e}"


# ------------------ Google Search (read aloud) ------------------
def summarize_text(text, max_chars=500):
    text = text.replace("\n", " ")
    if len(text) > max_chars:
        return text[:max_chars] + "..."
    return text

def handle_search(text):
    query = text
    for kw in ["search", "google", "look up", "find"]:
        query = query.replace(kw, "")
    query = query.strip()
    if not query:
        return "What should I search for?"

    try:
        results = list(search(query))
        if not results:
            return "I couldn't find anything."

        top_result = results[0]
        speak(f"I found some results for {query}. Reading the top result.")


        webbrowser.open(top_result)


        try:
            r = requests.get(top_result, timeout=5)
            soup = BeautifulSoup(r.text, "html.parser")
            paragraphs = soup.find_all("p")
            text_content = " ".join([p.get_text() for p in paragraphs[:3]])
            summary = summarize_text(text_content)
            if summary:
                speak(summary)
            else:
                speak("No readable text found on this page.")
        except Exception as e:
            speak(f"Couldn't read the page: {e}")

        return f"I read the top result for {query}."
    except Exception as e:
        return f"Error during search: {e}"

# ------------------ Greet Friend ------------------
def handle_greet_friend(text):
    doc = nlp(text)

    names = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]

    if not names:
        tokens = text.split()
        for i, token in enumerate(tokens):
            if token.lower() == "friend" and i + 1 < len(tokens):
                names.append(tokens[i + 1].capitalize())
                break


    if not names:
        names = [token.text for token in doc if token.text.istitle()]

    if names:
        all_names = ", ".join(names)
        return f"Hey {all_names}! How are you doing today?"
    else:
        return "Hello! Who am I greeting?"

# ------------------ Intent Handlers ------------------
def handle_sleep(intent):
    if intent in ["sleep", "standby"]:
        speak("Going back to standby. Say 'Jarvis' to wake me up again.")


def handle_intent(intent, text, ):
    if intent == "greeting":
        return "Hello! How can I help you?"
    elif intent == "exit":
        return "Goodbye!"
    elif intent == "sleep":
        return "Sleep Mode"
    elif intent == "greet_friend":
        return handle_greet_friend(text)
    elif intent == "weather":
        city = ask_city()
        return get_weather(city)
    elif intent == "time":
        return f"The time is {datetime.datetime.now().strftime('%H:%M:%S')}"
    elif intent == "date":
        return f"Today's date is {datetime.date.today().strftime('%B %d, %Y')}"
    elif intent == "system_command":
        return handle_system(text)
    elif intent == "file":
        return handle_file(text)
    elif intent == "wikipedia":
        return handle_wikipedia(text)
    elif intent == "reminder":
        return set_reminder()
    elif intent == "search":
        return handle_search(text)
    elif intent == "joke":
        rjoke = str(pyjokes.get_joke())
        return rjoke
    else:
        return "Hmm, I didn't understand that. Could you rephrase?"

# ------------------ Main AI Function ------------------
def ask_ai(prompt):
    intent = classify_intent(prompt)
    return handle_intent(intent, prompt)

# ------------------ Wake Word Listener ------------------
def listen_for_wake_word():
    while True:
        text = listen(timeout=3)
        if any(w in text for w in WAKE_WORDS):
            speak("Yes, I am listening. What can I do for you?")
            return True

# ------------------ Main Loop ------------------
def main():
    speak("Jarvis is online. Say 'Jarvis' to wake me up.")
    check_reminders()

    while True:
        if listen_for_wake_word():
            check_reminders()
            while True:
                check_reminders()
                user_input = listen()
                if not user_input:
                    continue

                user_input_lower = user_input.lower()
                if "sleep" in user_input_lower or 'stand by' in user_input_lower:
                    speak("Going back to standby. Say 'Jarvis' to wake me up again.")
                    break


                if user_input_lower in ["exit", "quit", "bye"]:
                    speak("Goodbye!")
                    return

                if user_input.startswith("!"):
                    command = user_input[1:]
                    try:
                        output = os.popen(command).read()
                        speak(output if output else "Command executed.")
                    except Exception as e:
                        speak(f"Error: {e}")
                else:
                    response = ask_ai(user_input)
                    speak(response)

if __name__ == "__main__":
    main()
