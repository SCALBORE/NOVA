"""
NOVA backend — wraps Qwen2.5-1.5B-Instruct behind a small HTTP API so the
web frontend (index.html) can talk to it.

This is the same model + generation logic as the original Colab script,
just reorganized so a browser can call it over HTTP instead of you typing
into input().

-----------------------------------------------------------------------
SETUP
-----------------------------------------------------------------------
1. Create a virtual environment (recommended) and install dependencies:

     pip install -r requirements.txt

2. Run the server:

     python app.py

   First run will download Qwen2.5-1.5B-Instruct from Hugging Face
   (a few GB), so make sure you have internet access and disk space.
   If you have a CUDA GPU it will be used automatically; otherwise it
   falls back to CPU (slower, but the model is small enough to be usable).

3. By default the server listens on http://localhost:8000
   The chat endpoint is:  POST http://localhost:8000/api/chat

4. Open index.html in your browser (just double-click it, or serve it
   with any static file server) and set CHAT_ENDPOINT in its <script>
   block to "http://localhost:8000/api/chat". It's already set up to
   send exactly the payload this server expects.

-----------------------------------------------------------------------
API CONTRACT
-----------------------------------------------------------------------
POST /api/chat
Request body:
    {
      "history": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
        ...
      ]
    }
    (This is exactly the `messages` list shape from the original script.
     The frontend keeps this list client-side and sends the whole thing
     on every turn, since the server itself is stateless between requests.)

Response body:
    { "reply": "Nova's reply text" }

Errors return: { "error": "message" } with an appropriate HTTP status.
"""

import os
import torch
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
MAX_NEW_TOKENS = 250
TEMPERATURE = 0.7
TOP_P = 0.9
REPETITION_PENALTY = 1.1

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Using device:", device)

print("Loading tokenizer and model (first run downloads the weights)...")
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
    )
    if device == "cpu":
        model.to(device)
    model.eval()
    print("Nova backend ready.")
except Exception as exc:
    raise RuntimeError(
        "Failed to load the model. Make sure you have internet access on "
        "first run (weights download from Hugging Face) and that "
        "'transformers', 'torch', and 'accelerate' are installed correctly. "
        f"Original error: {exc}"
    ) from exc

app = Flask(__name__)
CORS(app)  # allow the browser-hosted frontend to call this API


def generate_reply(messages):
    """Takes a full messages list (system/user/assistant turns) and returns
    Nova's next reply, using the same generation settings as the original
    Colab script."""
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=4096,
    ).to(model.device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            repetition_penalty=REPETITION_PENALTY,
            pad_token_id=tokenizer.eos_token_id,
        )

    new_tokens = output[0][inputs["input_ids"].shape[1]:]
    reply = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    return reply if reply else "I don't have a reply for that — could you rephrase?"


@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "service": "Nova backend",
        "status": "running",
        "endpoints": ["/api/chat (POST)", "/api/health (GET)"],
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    history = data.get("history")

    if not history or not isinstance(history, list):
        return jsonify({"error": "Request must include a non-empty 'history' list."}), 400

    # Basic shape validation so a malformed request fails clearly
    for turn in history:
        if "role" not in turn or "content" not in turn:
            return jsonify({"error": "Each history item needs 'role' and 'content'."}), 400

    try:
        reply = generate_reply(history)
    except Exception as exc:
        return jsonify({"error": f"Generation failed: {exc}"}), 500

    return jsonify({"reply": reply})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "device": device, "model": MODEL_NAME})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Threaded=False keeps generation requests serialized, which avoids
    # two requests fighting over the GPU/CPU at once on a single-model server.
    app.run(host="0.0.0.0", port=port, debug=False, threaded=False)
