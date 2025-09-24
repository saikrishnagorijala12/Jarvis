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
import inflect
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
import tempfile

p = inflect.engine()

# ------------------ Initialize ------------------
nlp = spacy.load("en_core_web_sm")
recognizer = sr.Recognizer()
# # tts = pyttsx3.init()
# tts.setProperty("rate", 160)
# tts.setProperty("volume", 1.0)
WAKE_WORDS = ["jarvis", "hey jarvis"]
reminders = []


# ------------------ Speak Function ------------------
def speak(text):
    print(f"Jarvis: {text}")
    try:
        tts = gTTS(text=text, lang='en')
        with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as fp:
            tts.save(fp.name)
            audio = AudioSegment.from_file(fp.name, format="mp3")
            play(audio)
    except Exception as e:
        print(f"Error in speak(): {e}")


# ------------------ Enhanced Listen Function ------------------
def listen(timeout=None, phrase_time_limit=None):
    with sr.Microphone(device_index=0) as source:
        # Adjust for ambient noise
        recognizer.adjust_for_ambient_noise(source, duration=0.5)

        if timeout:
            print(f"Listening for {timeout} seconds...")
        else:
            print("Listening...")

        try:
            # For short inputs, use phrase_time_limit to capture quick speech
            if phrase_time_limit is None:
                phrase_time_limit = 3  # Allow up to 3 seconds of speech

            audio = recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_time_limit
            )

            result = recognizer.recognize_google(audio).lower()
            print(f"Raw recognition result: '{result}'")  # Debug line
            return result

        except sr.UnknownValueError:
            print("Speech was unclear")  # Debug line
            return ""
        except sr.RequestError as e:
            speak(f"Speech service error: {e}")
            return ""
        except sr.WaitTimeoutError:
            print("Listening timeout - no speech detected")  # Debug line
            return ""


# ------------------ Specialized Number Listening Function ------------------
def listen_for_number(timeout=15, max_attempts=3):
    """Specialized function for listening to numbers with better sensitivity"""

    for attempt in range(max_attempts):
        with sr.Microphone(device_index=0) as source:
            # More aggressive noise adjustment for short sounds
            print(f"Adjusting for ambient noise (attempt {attempt + 1})...")
            recognizer.adjust_for_ambient_noise(source, duration=1.0)

            # Lower energy threshold for short sounds
            recognizer.energy_threshold = 300  # Lower threshold
            recognizer.dynamic_energy_threshold = True
            recognizer.pause_threshold = 0.5  # Shorter pause detection

            print(f"Listening for numbers (attempt {attempt + 1}/{max_attempts})...")

            try:
                # Listen with shorter phrase limit for single digits
                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=2,  # Shorter limit for single digits
                )

                result = recognizer.recognize_google(audio).lower()
                print(f"Attempt {attempt + 1} - Heard: '{result}'")

                if result.strip():  # If we got something
                    return result

            except sr.UnknownValueError:
                print(f"Attempt {attempt + 1} - Speech unclear")
            except sr.RequestError as e:
                print(f"Attempt {attempt + 1} - Service error: {e}")
            except sr.WaitTimeoutError:
                print(f"Attempt {attempt + 1} - Timeout")

        if attempt < max_attempts - 1:
            speak("I didn't catch that. Please speak a bit louder and clearer.")

    return ""


# ------------------ Preprocess ------------------
def preprocess(text):
    doc = nlp(text.lower())
    return [token.lemma_ for token in doc if token.is_alpha and not token.is_stop]


# ------------------ Intents ------------------
intents = {
    "greeting": ["hello", "hi", "hey", "morning"],
    "exit": ["bye", "quit", "exit"],
    "greet_friend": ["friend"],
    "weather": ["weather", "forecast", "temperature"],
    "time": ["time", "clock"],
    "date": ["date", "day", "today"],
    "system_command": [
        "open",
        "launch",
        "run",
        "shutdown",
        "restart",
        "volume",
        "brightness",
        "ip",
    ],
    "file": ["file", "folder", "directory", "create", "delete", "list"],
    "wikipedia": ["wikipedia", "who", "what", "tell me about"],
    "search": ["search", "google", "look up", "find"],
    "joke": ["joke", "funny", "laugh"],
    "sleep": ["sleep", "standby"],
    "reminder": ["remind", "reminder", "note"],
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


# ------------------ Enhanced Number Parser ------------------
def parse_number(text):
    """Convert spoken numbers to integers with comprehensive parsing"""
    if not text:
        return None

    # Clean the input
    text = text.lower().strip()

    # Remove common time-related words
    time_words = ["minutes", "minute", "mins", "min", "from", "now", "in", "after"]
    for word in time_words:
        text = text.replace(word, "").strip()

    # Try direct conversion first (for digits like "5", "15", "22")
    try:
        return int(text)
    except ValueError:
        pass

    # Comprehensive word-to-number dictionary
    word_to_num = {
        "zero": 0,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
        "twenty-one": 21,
        "twenty-two": 22,
        "twenty-three": 23,
        "twenty-four": 24,
        "twenty-five": 25,
        "twenty-six": 26,
        "twenty-seven": 27,
        "twenty-eight": 28,
        "twenty-nine": 29,
        "thirty": 30,
        "thirty-five": 35,
        "forty": 40,
        "forty-five": 45,
        "fifty": 50,
        "fifty-five": 55,
        "sixty": 60,
    }

    # Check for direct word match
    if text in word_to_num:
        return word_to_num[text]

    # Handle compound numbers like "twenty five" (with space)
    text_no_space = text.replace(" ", "-")
    if text_no_space in word_to_num:
        return word_to_num[text_no_space]

    # Handle cases like "2 5" being interpreted as "25"
    if " " in text:
        digits = text.split()
        if len(digits) == 2 and all(d.isdigit() for d in digits):
            return int("".join(digits))

    # Handle repeated words like "one one" = 11
    words = text.split()
    if len(words) == 2 and words[0] == words[1] and words[0] in word_to_num:
        digit = str(word_to_num[words[0]])
        return int(digit + digit)  # "one one" becomes 11

    # Handle cases where there might be extra words but a single number exists
    words = text.split()
    for word in words:
        try:
            return int(word)
        except ValueError:
            if word in word_to_num:
                return word_to_num[word]

    # Try using inflect library for more complex number parsing
    try:
        # Handle written numbers like "twenty-five", "thirty-seven"
        for num in range(1, 100):
            if (
                p.number_to_words(num).replace("-", " ") == text
                or p.number_to_words(num) == text
            ):
                return num
    except:
        pass

    return None


# ------------------ Enhanced Reminder System ------------------
def set_reminder():
    """Enhanced reminder function with better number recognition"""
    speak("What should I remind you about?")
    task = listen(timeout=10)
    if not task:
        speak("I didn't catch that. Please try again later.")
        return "Reminder not set."

    speak("When should I remind you? Please say the number of minutes clearly.")
    time_input = listen_for_number()

    print(f"DEBUG: Final time input: '{time_input}'")

    if not time_input:
        speak(
            "I couldn't hear the time after multiple attempts. Please try again later."
        )
        return "Reminder not set."

    minutes = parse_number(time_input)

    if minutes is None or minutes <= 0:
        speak(f"I couldn't understand '{time_input}' as a valid number of minutes.")
        return "Could not understand the time. Reminder not set."

    remind_time = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    reminders.append((remind_time, task))

    print(f"DEBUG: Set reminder for {minutes} minutes: {task}")
    return f"Reminder set for {minutes} minutes from now: {task}"


def check_reminders():
    now = datetime.datetime.now()
    for r in reminders[:]:
        remind_time, task = r
        if now >= remind_time:
            speak(f"Reminder: {task}")
            reminders.remove(r)


# ------------------ Weather Functions ------------------
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
        desc = res["weather"][0]["description"]
        temp = res["main"]["temp"]
        feels = res["main"]["feels_like"]
        humidity = res["main"]["humidity"]
        return f"Weather in {city}: {desc}, temperature {temp}°C, feels like {feels}°C, humidity {humidity}%."
    except Exception as e:
        return f"Error fetching weather: {e}"


# ------------------ Google Search Functions ------------------
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


# ------------------ Greet Friend Function ------------------
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


def handle_intent(intent, text):
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
                if "sleep" in user_input_lower or "stand by" in user_input_lower:
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

