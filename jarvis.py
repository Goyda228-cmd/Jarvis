import tkinter as tk
import threading
import requests
import queue
import speech_recognition as sr
import subprocess
import pyttsx3
import ctypes
import screen_brightness_control as sbc
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
import pyautogui
import random
import edge_tts
import asyncio
import pygame
import tempfile
import json
import os
import webbrowser
import pyautogui
import uuid
import asyncio
import sys
from reactor_ui import start_reactor
from voice import start_voice_mode
import tkinter as tk

def start_reactor():

    root = tk.Tk()
    root.title("Jarvis Reactor")
    root.geometry("400x500")

    chat = tk.Text(root)
    chat.pack(expand=True, fill="both")

    entry = tk.Entry(root)
    entry.pack(fill="x")

    def send(event=None):
        text = entry.get()
        chat.insert("end", "Вы: " + text + "\n")
        entry.delete(0, "end")

    entry.bind("<Return>", send)

    root.mainloop()

mode = "voice"

if len(sys.argv) > 1:
    mode = sys.argv[1]

if mode == "reactor":
    print("Запуск Reactor UI")
    start_reactor()

else:
    print("Запуск голосового режима")
    start_voice_mode()

pygame.mixer.init()

async def speak_async(text):
    filename = f"voice_{uuid.uuid4()}.mp3"

    communicate = edge_tts.Communicate(
        text=text,
        voice="ru-RU-DmitryNeural"
    )

    await communicate.save(filename)

    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)

# загружаем конфиг
with open("commands.json", "r", encoding="utf-8") as f:
    config = json.load(f)

commands = config["commands"]
mouse_settings = config["mouse"]
wake_words = config["voice"]["wake_words"]

# === НАСТРОЙКИ МЫШИ ===
MOUSE_STEP = 100
MOUSE_DURATION = 0.2

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

def start_voice_mode():

    print("Jarvis слушает...")

    while True:

        text = input("Вы: ")

        if text == "выход":
            break

        print("Jarvis:", text)

# ================= МЫШКА =================

def move_mouse(dx=0, dy=0):
    x, y = pyautogui.position()
    pyautogui.moveTo(
        x + dx,
        y + dy,
        duration=MOUSE_DURATION
    )

def click():
    pyautogui.click()

def double_click():
    pyautogui.doubleClick()

def right_click():
    pyautogui.rightClick()

def drag_mouse(dx=0, dy=0):
    x, y = pyautogui.position()
    pyautogui.dragTo(
        x + dx,
        y + dy,
        duration=MOUSE_DURATION,
        button='left'
    )

# ================= СИСТЕМА =================

def set_volume(level):
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = interface.QueryInterface(IAudioEndpointVolume)
    volume.SetMasterVolumeLevelScalar(level / 100, None)


def change_volume(delta):
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = interface.QueryInterface(IAudioEndpointVolume)
    current = volume.GetMasterVolumeLevelScalar()
    volume.SetMasterVolumeLevelScalar(
        max(0, min(1, current + delta)), None)


def set_brightness(level):
    sbc.set_brightness(level)

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

    for cmd in commands:

        for phrase in cmd["phrases"]:

            if phrase in text:

                action = cmd["action"]

                if action == "open_url":
                    webbrowser.open(cmd["value"])
                    return True

                elif action == "open_program":
                    os.system(cmd["value"])
                    return True

                elif action == "system":
                    os.system(cmd["value"])
                    return True

                elif action == "shutdown":
                    os.system("shutdown /s /t 1")
                    return True

                elif action == "restart":
                    os.system("shutdown /r /t 1")
                    return True

                elif action == "lock":
                    os.system("rundll32.exe user32.dll,LockWorkStation")
                    return True

                elif action == "exit":
                    print("Jarvis: выключаюсь")
                    os._exit(0)

    return False

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

def voice_loop():
    recognizer = sr.Recognizer()

    # === НАСТРОЙКИ ДЛЯ ШУМНОЙ СРЕДЫ ===
    recognizer.pause_threshold = 0.6
    recognizer.non_speaking_duration = 0.5
    recognizer.dynamic_energy_threshold = True
    recognizer.energy_threshold = 400  # выше = меньше реагирует на шум

    try:
        mic = sr.Microphone()
    except Exception as e:
        ui_queue.put(("text", f"Ошибка микрофона: {e}"))
        return

    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)

    ui_queue.put(("status", "Ожидание команды..."))

    while True:
        try:
            # === СЛУШАЕМ WAKE-СЛОВО ===
            with mic as source:
                audio = recognizer.listen(
                    source,
                    timeout=3,
                    phrase_time_limit=3
                )

            text = recognizer.recognize_google(
                audio,
                language="ru-RU"
            ).lower()

            print("Слышал:", text)

            # === УСТОЙЧИВАЯ ПРОВЕРКА ===
            if any(w in text for w in WAKE_WORDS) or \
               "джа" in text or \
               "жар" in text:

                ui_queue.put(("status", "Слушаю..."))

                # === СЛУШАЕМ КОМАНДУ ===
                with mic as source:
                    command_audio = recognizer.listen(
                        source,
                        timeout=3,
                        phrase_time_limit=4
                    )

                command = recognizer.recognize_google(
                    command_audio,
                    language="ru-RU"
                ).lower()

                print("Команда:", command)

                ui_queue.put(("text", "Ты: " + command))

                threading.Thread(
                    target=ai_worker,
                    args=(command,),
                    daemon=True
                ).start()

                ui_queue.put(("status", "Ожидание команды..."))

        except sr.WaitTimeoutError:
            continue

        except sr.UnknownValueError:
            continue

        except Exception as e:
            ui_queue.put(("text", f"Ошибка: {e}"))
            ui_queue.put(("status", "Ожидание команды..."))

def speak(text):
    async def _speak():
        voice = "ru-RU-DmitryNeural"  # мужской голос
        communicate = edge_tts.Communicate(text, voice)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            filename = f.name

        await communicate.save(filename)

        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    try:
        asyncio.run(_speak())
    except:
        pass

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

entry.bind("<Return>", lambda event: send_text())

def send_text():
    user_text = entry.get()
    entry.delete(0, tk.END)

    ui_queue.put(("text", "Ты: " + user_text))
    threading.Thread(target=ai_worker, args=(user_text,), daemon=True).start()


def start_voice():
    threading.Thread(target=voice_worker, daemon=True).start()

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
threading.Thread(target=voice_loop, daemon=True).start()
root.mainloop()