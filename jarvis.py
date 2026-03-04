import tkinter as tk
import threading
import requests
import queue
import speech_recognition as sr
import webbrowser
import subprocess
import pyttsx3
import os
import ctypes
import screen_brightness_control as sbc
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
import pyautogui

pyautogui.FAILSAFE = False
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

    if "youtube" in text:
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
        # ГРОМКОСТЬ
    if "громкость 100" in text:
        set_volume(100)
        return "Громкость 100 процентов"

    if "громкость 50" in text:
        set_volume(50)
        return "Громкость 50 процентов"

    if "тише" in text:
        change_volume(-0.1)
        return "Уменьшаю громкость"

    if "громче" in text:
        change_volume(0.1)
        return "Увеличиваю громкость"

    # ЯРКОСТЬ
    if "яркость 100" in text:
        set_brightness(100)
        return "Яркость на максимум"

    if "яркость 50" in text:
        set_brightness(50)
        return "Яркость 50 процентов"

    # БЛОКИРОВКА
    if "заблокируй" in text:
        ctypes.windll.user32.LockWorkStation()
        return "Блокирую компьютер"

    # ПЕРЕЗАГРУЗКА
    if "перезагрузи" in text:
        os.system("shutdown /r /t 5")
        return "Перезагрузка через 5 секунд"

    # ВЫКЛЮЧЕНИЕ
    if "выключи компьютер" in text:
        os.system("shutdown /s /t 5")
        return "Выключение через 5 секунд"

    # ДИСПЕТЧЕР ЗАДАЧ
    if "диспетчер задач" in text:
        os.system("taskmgr")
        return "Открываю диспетчер задач"

    # СПЯЩИЙ РЕЖИМ
    if "спящий режим" in text:
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return "Переход в спящий режим"
       
    global MOUSE_STEP, MOUSE_DURATION

    # === СКОРОСТЬ ===

    if "быстрее" in text:
        MOUSE_DURATION = max(0.01, MOUSE_DURATION - 0.05)
        return f"Скорость увеличена"

    if "медленнее" in text:
        MOUSE_DURATION += 0.05
        return f"Скорость уменьшена"

    if "скорость" in text:
        try:
            value = int(text.split()[-1])
            MOUSE_STEP = value
            return f"Шаг мыши {value} пикселей"
        except:
            return "Не понял значение скорости"

    # === ДВИЖЕНИЕ ===

    if "вправо" in text:
        move_mouse(MOUSE_STEP, 0)
        return "Двигаю вправо"

    if "влево" in text:
        move_mouse(-MOUSE_STEP, 0)
        return "Двигаю влево"

    if "вверх" in text:
        move_mouse(0, -MOUSE_STEP)
        return "Двигаю вверх"

    if "вниз" in text:
        move_mouse(0, MOUSE_STEP)
        return "Двигаю вниз"

    if "тащи вправо" in text:
        drag_mouse(MOUSE_STEP * 2, 0)
        return "Перетаскиваю вправо"

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