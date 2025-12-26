# Local HUD‑OCR LLM Setup with Ollama and Qwen3‑VL‑8B

This project uses a local vision‑language model (VLM) to read cropped HUD elements from game screenshots.  
The model runs locally via **Ollama** using **`qwen3-vl:8b`**, a multimodal model that understands images and text.

The guide covers setup on:

- Windows (native Ollama)
- Ubuntu & WSL (Ubuntu on Windows)

---

## 1. Requirements

- NVIDIA RTX GPU (RTX 4080/4090/50‑series or similar recommended for smooth vision inference).
- At least **16 GB system RAM** and **12–16 GB VRAM** for `qwen3-vl:8b` with reasonable performance.

---

## 2. Install Ollama on Windows

On Windows, Ollama runs as a background service and exposes an HTTP API on `http://localhost:11434`.

### 2.1 Download and install

1. Go to the official Ollama website and download the **Windows installer** (`OllamaSetup.exe`).  
2. Run the installer and follow the wizard (default options are fine).  
3. After installation, Ollama starts automatically and will launch on system startup unless disabled.

Verify the CLI:

```bash
ollama --version
```

You should see a version string.

### 2.2 Verify the local server

```bash
curl http://localhost:11434
```

Expected response:

```
Ollama is running
```

This confirms the HTTP API is live on `http://localhost:11434`.

---

## 3. Install Ollama on Ubuntu / WSL

The Linux installation works both on native Ubuntu and on **Ubuntu under WSL2 on Windows**.

### 3.1 Enable WSL2 on Windows (if needed)

From an **elevated PowerShell**:

```powershell
wsl --install
```

- This installs WSL2 and a default Ubuntu distribution. Reboot if requested.

Launch **Ubuntu** from the Start menu and create a Linux user.

### 3.2 Install Ollama in Ubuntu / WSL

In an Ubuntu terminal (native or WSL):

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

This installs Ollama and sets up a `systemd` service called `ollama`.

Verify:

```bash
ollama --version
systemctl status ollama
```

If systemd is not enabled in your WSL distro, start the server manually:

```bash
ollama serve
```

Leave this terminal open.

### 3.3 Ensure GPU access in WSL

Inside Ubuntu/WSL:

```bash
nvidia-smi
```

You should see your RTX GPU; otherwise GPU support is not available and Ollama will use CPU.

Optional GPU config:

```bash
mkdir -p ~/.ollama
cat << 'EOF' > ~/.ollama/config.yaml
use_cuda: true
num_gpu: 1
EOF
```

Restart Ollama:

```bash
sudo systemctl restart ollama  # or restart your ollama serve session
```

---

## 4. Pull and Test `qwen3-vl:8b`

### 4.1 Download the model

```bash
ollama pull qwen3-vl:8b
```

This downloads the ~13 GB multimodal model.

### 4.2 Quick CLI sanity check

Place a test HUD crop image in the current directory, e.g. `example1.jpg`, then run:

```bash
ollama run qwen3-vl:8b "
You see a cropped game UI element with an icon and some text.
Image: ./example1.jpg

Describe the numbers and the resource name you see."
```

Ollama automatically attaches the image path for vision‑enabled models.

---

## 5. Using the HTTP API from Python

The application calls Ollama at `http://localhost:11434/api/generate` on all platforms.

### 5.1 Helper: image to base64

```python
import base64
from io import BytesIO
from PIL import Image

def pil_to_base64(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")
```

### 5.2 Single‑image example

```python
import json
import requests
from PIL import Image

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3-vl:8b"

img = Image.open("example1.jpg")
b64 = pil_to_base64(img)

prompt = """
You see a cropped game UI element with an icon on the left.
To the right are two numbers in the format "required (available)".
Below that is the resource name (possibly multiple words).

Return ONLY one JSON object:

{
  "item_name": "<string>",
  "required_count": <integer>,
  "available_count": <integer>
}

Numbers must be integers without thousand separators.
"""

payload = {
    "model": MODEL_NAME,
    "prompt": prompt,
    "images": [b64],
    "stream": False,
}

resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
resp.raise_for_status()
response_text = resp.json()["response"]
data = json.loads(response_text)
print(data)
```

The `images` field is an array of base64‑encoded images, as required for vision models.

## 6. Troubleshooting

- **Server not reachable**

```bash
curl http://localhost:11434
```

If this fails, start or restart the Ollama service (`systemctl status ollama` on Ubuntu/WSL, or restart the Ollama app on Windows).

- **Very slow or timing out**
  - First calls may be slow while `qwen3-vl:8b` loads into memory.  
  - Increase the HTTP timeout in Python and monitor `ollama ps` / `nvidia-smi` for activity.

- **CPU instead of GPU**
  - In Ubuntu/WSL, ensure `nvidia-smi` works.  
  - Set `use_cuda: true` in `~/.ollama/config.yaml` and restart Ollama.

- **HTTP 400 / 500 errors**
  - 400 usually indicates malformed JSON (missing `model` or `prompt`, or wrong `images` type).  
  - 500 indicates a server‑side error; inspect Ollama logs via `journalctl -u ollama` or the `ollama serve` console.

---

## 7. Summary

Once Ollama is installed and `qwen3-vl:8b` is pulled, the same HTTP API works across:

- Native Windows  
- Native Ubuntu  
- Ubuntu/WSL on Windows  

The HUD‑OCR pipeline only needs `http://localhost:11434/api/generate` plus the JSON formats above to run all LLM inference locally.
