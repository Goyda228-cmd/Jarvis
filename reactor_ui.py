import tkinter as tk

def start_reactor():

    root = tk.Tk()
    root.title("Jarvis Reactor")
    root.geometry("400x500")

    label = tk.Label(root, text="Jarvis Reactor", font=("Arial", 20))
    label.pack(pady=20)

    root.mainloop()