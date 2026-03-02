import requests

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

        data = response.json()
        return data.get("response", "").strip()

    except Exception as e:
        print("ERROR:", e)
        return None


print("Jarvis console started. Напиши 'exit' чтобы выйти.")

while True:
    user_input = input("Ты: ")

    if user_input.lower() == "exit":
        break

    answer = ask_phi3(user_input)

    if answer:
        print("Jarvis:", answer)
    else:
        print("Нет ответа от модели.")