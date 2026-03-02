import sounddevice as sd
import numpy as np

duration = 3
samplerate = 16000

print("Говори...")

recording = sd.rec(int(duration * samplerate),
                   samplerate=samplerate,
                   channels=1,
                   dtype="int16")
sd.wait()

print("Максимальный уровень:", np.max(recording))