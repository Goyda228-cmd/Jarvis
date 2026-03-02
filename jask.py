import sounddevice as sd
import vosk
import json
import numpy as np
if __name__ == "__main__":
    print("Jarvis запускается...")
    listen()

def find_working_mic():
    print("🔎 Поиск активного микрофона...")

    devices = sd.query_devices()
    input_devices = []

    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            input_devices.append((i, dev))

    best_device = None
    best_level = 0

    for index, dev in input_devices:
        try:
            print(f"Проверка: {dev['name']}")

            with sd.InputStream(device=index, channels=1, samplerate=16000) as stream:
                data, _ = stream.read(4000)
                volume = np.linalg.norm(data)

                print("Уровень:", volume)

                if volume > best_level:
                    best_level = volume
                    best_device = index

        except Exception as e:
            continue

    if best_device is not None:
        print("✅ Выбран микрофон:", devices[best_device]["name"])
        return best_device
    else:
        print("❌ Микрофон не найден")
        return None


def listen():
    global AUDIO_LEVEL, recognized_text

    device_index = find_working_mic()

    if device_index is None:
        return ""

    model = vosk.Model("model")  # папка model должна быть рядом
    rec = vosk.KaldiRecognizer(model, 16000)

    with sd.RawInputStream(
        device=device_index,
        samplerate=16000,
        blocksize=8000,
        dtype="int16",
        channels=1
    ) as stream:

        print("🎤 Jarvis слушает...")

        while True:
            data, _ = stream.read(4000)

            audio_np = np.frombuffer(data, dtype=np.int16)
            volume = np.linalg.norm(audio_np)
            AUDIO_LEVEL = min(volume / 10000, 1)

            if rec.AcceptWaveform(bytes(data)):
                result = json.loads(rec.Result())
                text = result.get("text", "")
                if text:
                    print("Вы сказали:", text)
                    recognized_text = text
                    return text.lower()
