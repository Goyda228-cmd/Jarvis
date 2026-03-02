import tkinter as tk
import threading
import requests
import queue
import speech_recognition as sr
import webbrowser
import pyttsx3
import os

ui_queue = queue.Queue()
WAKE_WORDS = ("джарвис", "jarvis", "жарвис")

engine = pyttsx3.init()


# ================= ГОЛОС ОТВЕТ =================

def speak(text):
    try:
        engine.say(text)
        engine.runAndWait()
    except:
        pass


# ================= PHI-3 =================

def ask_phi3(prompt):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "phi3:mini",
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"Ошибка модели: {e}"


# ================= КОМАНДЫ =================

def run_command(text):
    text = text.lower()

    # STEAM (через протокол)
    if "стим" in text:
        try:
            os.startfile("steam://open/main")
            return "Запускаю Steam"
        except:
            return "Steam не найден"

    # TELEGRAM (через веб или протокол)
    if "телеграм" in text:
        try:
            os.startfile("tg://resolve")
            return "Открываю Telegram"
        except:
            webbrowser.open("https://web.telegram.org/k/")
            return "Открываю Telegram Web"

    if "ютуб" in text:
        webbrowser.open("https://youtube.com")
        return "Открываю YouTube"

    if "github" in text or "гитхаб" in text:
        webbrowser.open("https://github.com")
        return "Открываю GitHub"

    if "очисти" in text:
        ui_queue.put(("clear", None))
        return "Экран очищен"

    if "выход" in text:
        root.after(500, root.destroy)
        return "Выключаюсь"

    return None


# ================= AI =================

def ai_worker(prompt):
    ui_queue.put(("status", "Думаю..."))

    command_result = run_command(prompt)

    if command_result:
        ui_queue.put(("text", "Jarvis: " + command_result))
        speak(command_result)
        ui_queue.put(("status", "Готов"))
        return

    answer = ask_phi3(prompt)
    ui_queue.put(("text", "Jarvis: " + answer))
    speak(answer)
    ui_queue.put(("status", "Готов"))


# ================= ГОЛОС ВВОД =================

def voice_worker():
    recognizer = sr.Recognizer()

    try:
        mic = sr.Microphone()
    except Exception as e:
        ui_queue.put(("text", f"Ошибка микрофона: {e}"))
        return

    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)

    ui_queue.put(("status", "Слушаю..."))

    try:
        with mic as source:
            audio = recognizer.listen(source, phrase_time_limit=5)

        text = recognizer.recognize_google(audio, language="ru-RU").lower()

        # Wake word
        if any(w in text for w in WAKE_WORDS):
            speak("Слушаю")
            ui_queue.put(("status", "Готов"))
            return

        ui_queue.put(("text", "Ты: " + text))
        threading.Thread(target=ai_worker, args=(text,), daemon=True).start()

    except sr.UnknownValueError:
        ui_queue.put(("text", "Не понял речь"))
        ui_queue.put(("status", "Готов"))

    except Exception as e:
        ui_queue.put(("text", f"Ошибка: {e}"))
        ui_queue.put(("status", "Готов"))


# ================= UI =================

root = tk.Tk()
root.geometry("600x450")
root.title("Jarvis Ultimate")

chat_label = tk.Label(root, text="JARVIS ONLINE", font=("Segoe UI", 12),
                      wraplength=550, justify="left")
chat_label.pack(pady=20)

status_label = tk.Label(root, text="Готов", fg="gray")
status_label.pack()

entry = tk.Entry(root, width=70)
entry.pack(pady=10)


def send_text():
    user_text = entry.get()
    entry.delete(0, tk.END)

    ui_queue.put(("text", "Ты: " + user_text))
    threading.Thread(target=ai_worker, args=(user_text,), daemon=True).start()


def start_voice():
    threading.Thread(target=voice_worker, daemon=True).start()


tk.Button(root, text="Отправить", command=send_text).pack(pady=5)
tk.Button(root, text="🎤 Голос", command=start_voice).pack(pady=5)


def process_queue():
    while not ui_queue.empty():
        item = ui_queue.get()

        if item[0] == "text":
            chat_label.config(text=item[1])

        elif item[0] == "status":
            status_label.config(text=item[1])

        elif item[0] == "clear":
            chat_label.config(text="")

    root.after(100, process_queue)


process_queue()
root.mainloop()