import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import os
import re
import webbrowser
import time
import sys
import queue
import traceback

class YouTubeFetcherDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Shorts Fetcher - Control Panel")
        self.root.geometry("650x500")
        
        # Message Queue for thread-safe UI updates
        self.msg_queue = queue.Queue()
        
        self.api_process = None
        self.tunnel_process = None
        self.public_url = ""
        
        self.setup_ui()
        self.check_dependencies()
        
        # Start the queue checker
        self.root.after(100, self.process_queue)
        
    def setup_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg="#f0f0f0", pady=10)
        header_frame.pack(fill=tk.X)
        tk.Label(header_frame, text="YouTube Shorts Fetcher API", font=("Helvetica", 16, "bold"), bg="#f0f0f0").pack()
        tk.Label(header_frame, text="Stable Control Panel (v2.0)", font=("Helvetica", 9), bg="#f0f0f0", fg="#666").pack()

        # Status Frame
        status_frame = tk.LabelFrame(self.root, text=" System Status ", padx=15, pady=10)
        status_frame.pack(padx=20, pady=10, fill=tk.X)
        
        self.api_status_label = tk.Label(status_frame, text="API Server: STOPPED", fg="red", font=("Helvetica", 10, "bold"))
        self.api_status_label.pack(anchor="w")
        
        self.tunnel_status_label = tk.Label(status_frame, text="Internet Tunnel: DISCONNECTED", fg="red", font=("Helvetica", 10, "bold"))
        self.tunnel_status_label.pack(anchor="w")
        
        # URL Frame
        url_frame = tk.Frame(self.root)
        url_frame.pack(padx=20, pady=5, fill=tk.X)
        tk.Label(url_frame, text="Public URL:", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        self.url_entry = tk.Entry(url_frame, font=("Consolas", 10), width=50)
        self.url_entry.pack(side=tk.LEFT, padx=10)
        
        # Buttons
        btn_frame = tk.Frame(self.root, pady=10)
        btn_frame.pack()
        
        self.start_btn = ttk.Button(btn_frame, text="START ALL", command=self.start_all)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="STOP ALL", command=self.stop_all, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.test_btn = ttk.Button(btn_frame, text="TEST LOCAL", command=self.test_local)
        self.test_btn.pack(side=tk.LEFT, padx=5)

        self.open_btn = ttk.Button(btn_frame, text="OPEN PUBLIC", command=self.open_public, state=tk.DISABLED)
        self.open_btn.pack(side=tk.LEFT, padx=5)
        
        # Log area
        log_frame = tk.Frame(self.root)
        log_frame.pack(padx=20, pady=5, fill=tk.BOTH, expand=True)
        tk.Label(log_frame, text="Activity Logs:", font=("Helvetica", 8)).pack(anchor="w")
        
        self.log_text = tk.Text(log_frame, height=10, font=("Consolas", 9), bg="#1e1e1e", fg="#dcdcdc", state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar for log
        scrollbar = tk.Scrollbar(self.log_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)

    def log(self, message):
        self.msg_queue.put(("log", message))

    def update_status(self, component, status, color):
        self.msg_queue.put(("status", (component, status, color)))

    def process_queue(self):
        try:
            while True:
                task, data = self.msg_queue.get_nowait()
                if task == "log":
                    self.log_text.config(state=tk.NORMAL)
                    self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {data}\n")
                    self.log_text.see(tk.END)
                    self.log_text.config(state=tk.DISABLED)
                elif task == "status":
                    comp, txt, col = data
                    if comp == "api":
                        self.api_status_label.config(text=f"API Server: {txt}", fg=col)
                    elif comp == "tunnel":
                        self.tunnel_status_label.config(text=f"Internet Tunnel: {txt}", fg=col)
                elif task == "url":
                    self.url_entry.delete(0, tk.END)
                    self.url_entry.insert(0, data)
                    self.public_url = data
                    self.open_btn.config(state=tk.NORMAL)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def check_dependencies(self):
        self.log("Checking dependencies...")
        missing = []
        for lib in ["fastapi", "uvicorn", "requests", "brotli", "youtube_transcript_api"]:
            try:
                __import__(lib)
            except ImportError:
                missing.append(lib)
        
        if missing:
            self.log(f"MISSING: {', '.join(missing)}")
            messagebox.showwarning("Missing Dependencies", f"Please run: pip install {' '.join(missing)}")
        else:
            self.log("All dependencies found.")

    def start_all(self):
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.log("Starting all services...")
        
        # Start API
        threading.Thread(target=self.run_api, daemon=True).start()
        # Start Tunnel (Delay 2s)
        self.root.after(2000, lambda: threading.Thread(target=self.run_tunnel, daemon=True).start())

    def run_api(self):
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # Check both possible locations
            api_script = os.path.join(base_dir, "youtube api", "short_api.py")
            if not os.path.exists(api_script):
                api_script = os.path.join(base_dir, "short_api.py")
            
            if not os.path.exists(api_script):
                self.log(f"❌ ERROR: short_api.py not found in {base_dir}")
                self.update_status("api", "FILE NOT FOUND", "red")
                return

            self.log(f"Spawning API: {sys.executable} \"{api_script}\"")
            self.api_process = subprocess.Popen(
                [sys.executable, api_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            self.update_status("api", "STARTING...", "orange")
            
            for line in iter(self.api_process.stdout.readline, ''):
                l = line.strip()
                if l:
                    self.log(f"API: {l}")
                    if "Uvicorn running" in l:
                        self.update_status("api", "RUNNING", "green")
                        self.log("SUCCESS: API is READY locally.")

        except Exception as e:
            self.log(f"❌ API CRASH: {str(e)}")
            self.log(traceback.format_exc())
            self.update_status("api", "FAILED", "red")

    def run_tunnel(self):
        try:
            self.log("Opening SSH Tunnel via localhost.run...")
            self.update_status("tunnel", "CONNECTING...", "orange")
            
            cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:127.0.0.1:7861", "nokey@localhost.run"]
            
            self.tunnel_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                stdin=subprocess.PIPE
            )
            
            for line in iter(self.tunnel_process.stdout.readline, ''):
                l = line.strip()
                if l:
                    # self.log(f"Tunnel: {l}") # Optional: noise reduction
                    match = re.search(r'https://[a-zA-Z0-9-]+\.(?:lhr\.life|lvh\.me)', l)
                    if match:
                        url = match.group(0)
                        self.msg_queue.put(("url", url))
                        self.update_status("tunnel", "CONNECTED", "green")
                        self.log(f"SUCCESS: PUBLIC URL: {url}")

        except Exception as e:
            self.log(f"❌ Tunnel ERROR: {str(e)}")
            self.update_status("tunnel", "FAILED", "red")

    def stop_all(self):
        self.log("Stopping all processes...")
        if self.api_process:
            self.kill_proc(self.api_process.pid)
            self.api_process = None
        if self.tunnel_process:
            self.kill_proc(self.tunnel_process.pid)
            self.tunnel_process = None
            
        self.update_status("api", "STOPPED", "red")
        self.update_status("tunnel", "DISCONNECTED", "red")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.open_btn.config(state=tk.DISABLED)
        self.msg_queue.put(("url", ""))

    def kill_proc(self, pid):
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
        except:
            pass

    def test_local(self):
        def _test():
            self.log("Testing local connection to http://127.0.0.1:7861...")
            try:
                import requests
                r = requests.get("http://127.0.0.1:7861/", timeout=3)
                if r.status_code == 200:
                    self.log("✅ SUCCESS: API responded on 127.0.0.1!")
                    self.update_status("api", "RUNNING", "green")
                else:
                    self.log(f"⚠️ API responded with status {r.status_code}")
            except Exception as e:
                self.log(f"❌ FAIL: API is NOT reachable locally: {str(e)}")
        
        threading.Thread(target=_test, daemon=True).start()

    def open_public(self):
        if self.public_url:
            webbrowser.open(f"{self.public_url}/docs")

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeFetcherDashboard(root)
    root.mainloop()
