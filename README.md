# Nova

A chat interface for a local Qwen2.5-1.5B-Instruct model, styled with a
full-bleed background image and light-grey / dark-grey chat bubbles.

## What's in this repo

| File | Purpose |
|---|---|
| `index.html` | The frontend — chat UI, styling, and the JS that talks to the backend. |
| `nova-bg.png` | Background image used by the frontend. |
| `app.py` | Flask backend that loads Qwen2.5-1.5B-Instruct and serves `/api/chat`. |
| `requirements.txt` | Python dependencies for `app.py`. |
| `Procfile` | Tells hosts like Render/Railway how to start the backend. |

## Important: this is two separate pieces

`index.html` is a static file — GitHub Pages can host it directly.
`app.py` is a Python server that needs to actually *run* somewhere with
enough CPU/RAM (or a GPU) to load the model. **GitHub Pages cannot run
Python**, so the backend needs its own host. This is normal for any
site with a real backend, not a limitation specific to this project.

## 1. Run it locally first

```bash
pip install -r requirements.txt
python app.py
```

This starts the backend at `http://localhost:8000`. The model downloads
from Hugging Face on first run (a few GB), so make sure you have internet
access and disk space the first time.

Then just open `index.html` in your browser. It's already pointed at
`http://localhost:8000/api/chat`, so it works immediately.

## 2. Put it on GitHub

```bash
git init
git add .
git commit -m "Nova chat interface"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

Model weights are **not** committed — they download at runtime, so the repo
stays small.

## 3. Host the frontend (GitHub Pages)

In your repo: **Settings → Pages → Deploy from a branch → main → / (root)**.
Your site will be live at `https://<your-username>.github.io/<your-repo>/`.

As-is, this gives you the working chat UI, but it won't be able to reach
`localhost:8000` from a visitor's browser — that address only exists on
your own machine. To get live replies for visitors, do step 4.

## 4. Host the backend somewhere it can actually run

Pick one (all have free tiers as of writing, worth double-checking current
pricing/limits):

- **Hugging Face Spaces** (Docker SDK) — a natural fit since the model
  itself comes from Hugging Face.
- **Render** or **Railway** — point them at this repo; they'll use
  `requirements.txt` and `Procfile` automatically.

Whichever you pick, once it's live you'll get a URL like
`https://your-backend.onrender.com`. Update the frontend:

```js
const CHAT_ENDPOINT = "https://your-backend.onrender.com/api/chat";
```

**One thing to watch for:** GitHub Pages serves over `https://`. Browsers
block a secure page from calling an insecure (`http://`) backend — this is
called mixed content, not a bug in this code. Make sure your backend host
gives you an `https://` URL (Render, Railway, and HF Spaces all do this by
default).

## API contract (if you want to swap in your own backend)

```
POST /api/chat
Body:  { "history": [ {"role": "system"|"user"|"assistant", "content": "..."} ] }
Reply: { "reply": "..." }
```

The frontend keeps the full conversation client-side and resends it each
turn, so the server itself stays stateless.
