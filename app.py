import datetime
import speech_recognition as sr
import pyttsx3
import spacy
import subprocess
import wikipedia
import requests
import pyjokes
import ollama
import threading
import time
from TTS.api import TTS
import simpleaudio as sa
import logging
import os
import contextlib
import io
import pickle
import shutil
from duckduckgo_search import DDGS
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter

try:
    import PyPDF2
    from docx import Document
except ImportError:
    os.system("pip install PyPDF2 python-docx")

# ------------------ Initialization ------------------
nlp = spacy.load("en_core_web_sm")
recognizer = sr.Recognizer()
tts = pyttsx3.init()
tts.setProperty('rate', 165)
tts.setProperty('volume', 1.0)
WAKE_WORDS = ["friday", "hey friday"]
thinking_flag = False
tts_model = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False, gpu=False)

@contextlib.contextmanager
def suppress_stdout_stderr():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
logging.getLogger('TTS').setLevel(logging.FATAL)
logging.getLogger('numba').setLevel(logging.WARNING)
logging.getLogger('torch').setLevel(logging.ERROR)

# ------------------ RAG Setup ------------------
VECTOR_STORE_PATH = "vector_store/faiss_index"
EMBEDDING_PATH = "vector_store/embeddings.pkl"

embedding_model = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
vector_store = None

def save_vector_store():
    if vector_store:
        os.makedirs(os.path.dirname(VECTOR_STORE_PATH), exist_ok=True)
        vector_store.save_local(VECTOR_STORE_PATH)
        with open(EMBEDDING_PATH, "wb") as f:
            pickle.dump(embedding_model, f)
        print("✅ Knowledge base saved.")

def load_vector_store():
    global vector_store, embedding_model
    if os.path.exists(VECTOR_STORE_PATH) and os.path.exists(EMBEDDING_PATH):
        with open(EMBEDDING_PATH, "rb") as f:
            embedding_model = pickle.load(f)
        vector_store = FAISS.load_local(VECTOR_STORE_PATH, embedding_model, allow_dangerous_deserialization=True)
        print("✅ Knowledge base loaded.")
    else:
        print("ℹ️ No knowledge base found.")

# ------------------ File Reading ------------------
def read_txt(file): return open(file, "r", encoding="utf-8", errors="ignore").read()
def read_pdf(file):
    text = ""
    with open(file, "rb") as f:
        pdf = PyPDF2.PdfReader(f)
        for page in pdf.pages: text += page.extract_text() or ""
    return text
def read_docx(file): return "\n".join([p.text for p in Document(file).paragraphs])

def ingest_document(file):
    global vector_store
    if not os.path.exists(file): return "File not found."
    ext = os.path.splitext(file)[1].lower()
    if ext == ".txt": text = read_txt(file)
    elif ext == ".pdf": text = read_pdf(file)
    elif ext == ".docx": text = read_docx(file)
    else: return "Unsupported file format."

    docs = text_splitter.create_documents([text])
    vector_store = FAISS.from_documents(docs, embedding_model) if vector_store is None else vector_store.add_documents(docs)
    save_vector_store()
    return f"📘 Learned from {os.path.basename(file)}."

def retrieve_context(query, k=3):
    if not vector_store: return ""
    results = vector_store.similarity_search(query, k=k)
    return "\n\n".join([r.page_content for r in results])

def clear_knowledge():
    global vector_store
    if os.path.exists("vector_store"): shutil.rmtree("vector_store")
    vector_store = None
    return "Knowledge base cleared."

# ------------------ Online Search ------------------
def web_search(query, num_results=3):
    """DuckDuckGo Search Fallback."""
    try:
        results = DDGS().text(query, max_results=num_results)
        summary = ""
        for r in results:
            summary += f"• {r['title']}: {r['body']}\n"
        return summary or "No results found."
    except Exception as e:
        return f"Search error: {e}"

# ------------------ LLaMA + RAG ------------------
def ask_llama(prompt):
    global thinking_flag
    thinking_flag = True
    t = threading.Thread(target=show_thinking)
    t.start()
    try:
        local_context = retrieve_context(prompt)
        online_context = web_search(prompt) if not local_context else ""
        context = (local_context + "\n\n" + online_context).strip()

        full_prompt = (
            "You are Friday, a factual assistant. Use context below to answer:\n\n"
            f"Context:\n{context}\n\nUser: {prompt}"
        )

        response = ollama.chat(
            model="friiday",
            messages=[
                {"role": "system", "content": "You are Friday, a precise and polite AI assistant."},
                {"role": "user", "content": full_prompt}
            ]
        )
        return response['message']['content']
    finally:
        thinking_flag = False
        t.join()

def show_thinking():
    global thinking_flag
    dots = [".", "..", "..."]
    speak("Let me think for a second.")
    i = 0
    while thinking_flag:
        print(f"\rFriday is thinking{dots[i % 3]}", end="", flush=True)
        time.sleep(0.5)
        i += 1
    print("\r", end="")

# ------------------ Speak ------------------
def speak(text):
    print(f"Friday: {text}")
    file = "voice.wav"
    with suppress_stdout_stderr(): tts_model.tts_to_file(text=text, file_path=file)
    sa.WaveObject.from_wave_file(file).play().wait_done()

# ------------------ Listen ------------------
def listen(timeout=None):
    with sr.Microphone() as src:
        try:
            audio = recognizer.listen(src, timeout=timeout)
            return recognizer.recognize_google(audio).lower()
        except: return ""

# ------------------ Intent Handling ------------------
def classify_intent(text):
    text = text.lower()
    if any(w in text for w in ["ingest", "learn", "upload"]): return "ingest"
    if "clear" in text and "knowledge" in text: return "clear"
    if any(w in text for w in ["search", "google", "find"]): return "search"
    if any(w in text for w in ["bye", "exit", "quit"]): return "exit"
    if any(w in text for w in ["hi", "hello", "hey"]): return "greet"
    return "chat"

def handle_intent(intent, text):
    if intent == "ingest":
        parts = text.split()
        file = parts[-1] if len(parts) > 1 else ""
        return ingest_document(file)
    elif intent == "clear": return clear_knowledge()
    elif intent == "search": return ask_llama(text)
    elif intent == "exit": return "Goodbye!"
    elif intent == "greet": return "Hello! How can I assist you today?"
    else: return ask_llama(text)

# ------------------ Core ------------------
def ask_ai(prompt):
    intent = classify_intent(prompt)
    return handle_intent(intent, prompt), intent

# ------------------ Wake Word ------------------
def listen_for_wake_word():
    while True:
        text = listen(timeout=3)
        if any(w in text for w in WAKE_WORDS):
            speak("Yes, I'm listening. What can I do?")
            return True

# ------------------ Main ------------------
def main():
    load_vector_store()
    speak("Friday is online. Say 'Friday' to wake me up.")
    while True:
        if listen_for_wake_word():
            while True:
                user_input = listen()
                if not user_input: continue
                if "exit" in user_input.lower(): 
                    speak("Goodbye!")
                    return
                response, _ = ask_ai(user_input)
                speak(response)

if __name__ == "__main__":
    main()
