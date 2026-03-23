import tkinter as tk
import threading
import requests
import queue
import speech_recognition as sr
import screen_brightness_control as sbc
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
import pyautogui
import edge_tts
import asyncio
import pygame
import json
import os
import webbrowser
import uuid
import time
import subprocess

def animate():
    global angle

    angle += 2

    for i, seg in enumerate(segments):
        canvas.itemconfig(seg, start=angle + i * 30)

    pulse = 8 * math.sin(angle * 0.05)

    canvas.coords(
        core,
        200 - pulse,
        150 - pulse,
        300 + pulse,
        250 + pulse
    )

    root.after(30, animate)

def set_state(state):

    if state == "idle":
        color = "#0ea5e9"
        text = "ОЖИДАНИЕ"

    elif state == "listening":
        color = "#22c55e"
        text = "СЛУШАЮ"

    elif state == "thinking":
        color = "#eab308"
        text = "ДУМАЮ"

    elif state == "error":
        color = "#ef4444"
        text = "ОШИБКА"

    canvas.itemconfig(core, fill=color)
    canvas.itemconfig(reactor_text, text=text)

    for ring in rings:
        canvas.itemconfig(ring, outline=color)

    for seg in segments:
        canvas.itemconfig(seg, outline=color)

def is_ollama_running():
    try:
        requests.get("http://localhost:11434", timeout=1)
        return True
    except:
        return False
    
def start_ollama():
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except Exception as e:
        ui_queue.put(("text", f"Ollama не запустилась: {e}"))
        return False

def wait_for_ollama(timeout=15):
    start_time = time.time()

    while time.time() - start_time < timeout:
        if is_ollama_running():
            return True
        time.sleep(1)

    return False

pygame.mixer.init()

async def speak_async(text):
    filename = f"voice_{uuid.uuid4()}.mp3"

    try:
        communicate = edge_tts.Communicate(
            text=text,
            voice="ru-RU-DmitryNeural"
        )

        await communicate.save(filename)

        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)

    finally:
        # 🔥 гарантированное удаление файла
        try:
            pygame.mixer.music.unload()  # освобождаем файл
        except:
            pass

        if os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception as e:
                print("Не удалось удалить файл:", e)
                
# загружаем конфиг
with open("commands.json", "r", encoding="utf-8") as f:
    config = json.load(f)

commands = config["commands"]
mouse_settings = config["mouse"]

# === НАСТРОЙКИ МЫШИ ===
MOUSE_STEP = 100
MOUSE_DURATION = 0.2

ui_queue = queue.Queue()
WAKE_WORDS = ("джарвис", "jarvis", "жарвис")

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

# ================= ГОЛОС ВВОД =================

def voice_loop():
    recognizer = sr.Recognizer()

    recognizer.pause_threshold = 0.6
    recognizer.non_speaking_duration = 0.5
    recognizer.dynamic_energy_threshold = True
    recognizer.energy_threshold = 400

    try:
        mic = sr.Microphone()
    except Exception as e:
        ui_queue.put(("text", f"Ошибка микрофона: {e}"))
        return

    ui_queue.put(("status", "Ожидание команды..."))

    while True:
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = recognizer.listen(
                    source,
                    timeout=5,
                    phrase_time_limit=5
                )

            text = recognizer.recognize_google(audio, language="ru-RU").lower()
            print("Слышал:", text)

            if any(w in text for w in WAKE_WORDS) or "джа" in text or "жар" in text:
                ui_queue.put(("status", "Слушаю..."))

                with mic as source:
                    command_audio = recognizer.listen(
                        source,
                        timeout=5,
                        phrase_time_limit=5
                    )

                command = recognizer.recognize_google(command_audio, language="ru-RU").lower()
                print("Команда:", command)
                ui_queue.put(("text", "Ты: " + command))

                threading.Thread(target=ai_worker, args=(command,), daemon=True).start()
                ui_queue.put(("status", "Ожидание команды..."))

        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except Exception as e:
            ui_queue.put(("text", f"Ошибка: {e}"))
            ui_queue.put(("status", "Ожидание команды..."))

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

def ask_phi3(prompt):

    if not is_ollama_running():
        ui_queue.put(("text", "Jarvis: Запускаю Ollama..."))
        
        if not start_ollama():
            return "Не удалось запустить Ollama"

        if not wait_for_ollama():
            return "Ollama не отвечает"

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
                    return "Открываю"

                elif action == "open_program":
                    os.system(cmd["value"])
                    return "Сейчас будет!"

                elif action == "system":
                    os.system(cmd["value"])
                    return "Хорошо"

                elif action == "shutdown":
                    os.system("shutdown /s /t 1")
                    return "Секунду!.."

                elif action == "restart":
                    os.system("shutdown /r /t 1")
                    return "Готовлюсь..."

                elif action == "lock":
                    os.system("rundll32.exe user32.dll,LockWorkStation")
                    return "Блок ставим значит?"

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
        asyncio.run(speak_async(command_result))
        ui_queue.put(("status", "Готов"))
        return

    answer = ask_phi3(prompt)
    ui_queue.put(("text", "Jarvis: " + answer))
    asyncio.run(speak_async(answer))
    ui_queue.put(("status", "Готов"))
    
# ================= UI =================

root = tk.Tk()
root.geometry("650x500")
root.title("Jarvis AI")

root.configure(bg="#0f172a")  # тёмный фон

import math

canvas = tk.Canvas(root, width=500, height=400, bg="#020617", highlightthickness=0)
canvas.pack()

cx, cy = 250, 200

rings = []
segments = []
angle = 0

# кольца
for r in range(100, 180, 20):
    ring = canvas.create_oval(
        cx - r, cy - r,
        cx + r, cy + r,
        outline="#0ea5e9",
        width=1
    )
    rings.append(ring)

# ядро
core = canvas.create_oval(200, 150, 300, 250, fill="#0ea5e9", outline="")

# сегменты
for i in range(12):
    seg = canvas.create_arc(
        150, 100, 350, 300,
        start=i * 30,
        extent=10,
        style="arc",
        outline="#38bdf8",
        width=2
    )
    segments.append(seg)

# текст
reactor_text = canvas.create_text(
    cx, cy,
    text="JARVIS",
    fill="white",
    font=("Segoe UI", 14, "bold")
)

status_label = tk.Label(
    root,
    text="Готов",
    fg="#94a3b8",
    bg="#0f172a",
    font=("Segoe UI", 10)
)
status_label.pack()

entry = tk.Entry(
    root,
    width=70,
    font=("Segoe UI", 11),
    bg="#1e293b",
    fg="white",
    insertbackground="white",
    relief="flat"
)
entry.pack(pady=15, ipady=6)

def process_queue():
    while not ui_queue.empty():
        item = ui_queue.get()

        if item[0] == "text":
            pass  # или убери вообще chat_label

        elif item[0] == "status":
            status_label.config(text=item[1])

            if "Ожидание" in item[1]:
                set_state("idle")

            elif "Слушаю" in item[1]:
                set_state("listening")

            elif "Думаю" in item[1]:
                set_state("thinking")

    root.after(100, process_queue)

def on_enter(event):
    command = entry.get().strip()
    if command:
        ui_queue.put(("text", "Ты: " + command))
        threading.Thread(target=ai_worker, args=(command,), daemon=True).start()
        entry.delete(0, tk.END)  # очищаем поле после отправки

entry.bind("<Return>", on_enter)

process_queue()
threading.Thread(target=voice_loop, daemon=True).start()
animate()
root.mainloop()