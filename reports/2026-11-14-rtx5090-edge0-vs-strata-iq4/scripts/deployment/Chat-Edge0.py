"""Chat with the running Edge0 service. Type /new or /quit."""
import json
import urllib.error
import urllib.request

messages = []
print("Edge0 local chat. /new starts a new conversation. /quit exits.")
while True:
    try:
        text = input("\nYou> ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if text == "/quit":
        break
    if text == "/new":
        messages.clear()
        print("New conversation.")
        continue
    if not text:
        continue
    messages.append({"role": "user", "content": text})
    payload = {
        "model": "edge0-145b-nvfp4", "messages": messages,
        "max_tokens": 2048, "reasoning_effort": "none", "stream": True,
    }
    req = urllib.request.Request(
        "http://127.0.0.1:18089/v1/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    answer = ""
    print("Edge0> ", end="", flush=True)
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            for line in response:
                if not line.startswith(b"data: ") or line.strip() == b"data: [DONE]":
                    continue
                event = json.loads(line[6:])
                for choice in event.get("choices", []):
                    delta = choice.get("delta", {}).get("content") or ""
                    answer += delta
                    print(delta, end="", flush=True)
        print()
    except (OSError, urllib.error.URLError, ValueError) as error:
        messages.pop()
        print(f"\nRequest failed: {error}")
        continue
    messages.append({"role": "assistant", "content": answer})
