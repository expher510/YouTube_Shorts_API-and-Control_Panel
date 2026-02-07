import customtkinter as ctk
import threading
import uvicorn
import sys
import os
import webbrowser
from PIL import Image
from pyngrok import ngrok, conf

# Import the API app from our existing file
sys.path.append(os.getcwd())
try:
    from short_api import app
except ImportError:
    app = None

# --- CONFIG ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- NGROK SETUP (BUNDLED) ---
def setup_ngrok_path():
    """Sets the ngrok path to the bundled executable if available."""
    if getattr(sys, 'frozen', False):
        # If running as EXE, look in _MEIPASS
        bundled_path = os.path.join(sys._MEIPASS, "ngrok.exe")
        if os.path.exists(bundled_path):
            conf.get_default().ngrok_path = bundled_path
            return True
    else:
        # If local, look in current dir
        local_path = os.path.join(os.getcwd(), "ngrok.exe")
        if os.path.exists(local_path):
            conf.get_default().ngrok_path = local_path
            return True
    return False

# Attempt to set path immediately
setup_ngrok_path()

class APIApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Shorts Smart Fetcher")
        self.geometry("650x550")
        self.resizable(False, False)
        
        # Server Thread
        self.server_thread = None
        self.is_running = False
        self.port = 7861
        self.public_url = None

        # --- UI LAYOUT ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Content
        self.grid_rowconfigure(2, weight=0)  # Logs/Status

        # 1. Header Frame
        self.header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        self.lbl_title = ctk.CTkLabel(self.header_frame, text="YouTube Shorts API", font=("Roboto", 24, "bold"))
        self.lbl_title.pack(side="left")

        self.btn_github = ctk.CTkButton(self.header_frame, text="GitHub Repo", width=120, command=self.open_github)
        self.btn_github.pack(side="right")

        # 2. Control Panel
        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        self.lbl_status = ctk.CTkLabel(self.main_frame, text="Status: STOPPED", font=("Roboto", 16), text_color="red")
        self.lbl_status.pack(pady=(20, 10))

        # Buttons Row
        self.buttons_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.buttons_frame.pack(pady=10)

        self.btn_toggle = ctk.CTkButton(self.buttons_frame, text="Start Local Server", font=("Roboto", 16, "bold"), 
                                        height=40, width=200, fg_color="green", hover_color="darkgreen",
                                        command=self.toggle_server)
        self.btn_toggle.pack(side="left", padx=10)

        self.btn_online = ctk.CTkButton(self.buttons_frame, text="Go Online (ngrok)", font=("Roboto", 16, "bold"),
                                        height=40, width=200, fg_color="#3B8ED0", hover_color="#2B6EA0",
                                        command=self.toggle_online, state="disabled")
        self.btn_online.pack(side="left", padx=10)

        # URL Display
        self.lbl_url = ctk.CTkLabel(self.main_frame, text="http://localhost:7861", font=("Consolas", 14), text_color="gray")
        self.lbl_url.pack(pady=5)
        self.lbl_url.bind("<Button-1>", lambda e: self.open_browser(None))
        
        self.lbl_public = ctk.CTkLabel(self.main_frame, text="Public URL: (Not Connected)", font=("Consolas", 14), text_color="gray")
        self.lbl_public.pack(pady=5)
        self.lbl_public.bind("<Button-1>", lambda e: self.open_browser(self.public_url))


        # Token Input
        self.token_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.token_frame.pack(pady=10)
        
        self.entry_token = ctk.CTkEntry(self.token_frame, placeholder_text="Enter ngrok Authtoken", width=250)
        self.entry_token.pack(side="left", padx=5)
        
        self.btn_save_token = ctk.CTkButton(self.token_frame, text="Save Token", width=100, command=self.save_token)
        self.btn_save_token.pack(side="left", padx=5)


        # 3. Actions / Quick Links
        self.actions_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.actions_frame.pack(pady=20, fill="x", padx=40)
        
        self.btn_docs = ctk.CTkButton(self.actions_frame, text="Open Swagger Docs", command=self.open_docs, state="disabled")
        self.btn_docs.pack(side="left", expand=True, padx=5)
        
        self.btn_test = ctk.CTkButton(self.actions_frame, text="Test Search (Cats)", command=self.open_test, state="disabled")
        self.btn_test.pack(side="right", expand=True, padx=5)

        # 4. Footer
        self.footer_frame = ctk.CTkFrame(self, height=40, corner_radius=0)
        self.footer_frame.grid(row=2, column=0, sticky="ew")
        
        self.lbl_info = ctk.CTkLabel(self.footer_frame, text="Ready to extract rich metadata...", font=("Roboto", 12))
        self.lbl_info.pack(pady=10)
        
    # --- LOGIC ---

    def save_token(self):
        token = self.entry_token.get().strip()
        if token:
            try:
                # Force kill any existing process to be safe
                ngrok.kill()
                ngrok.set_auth_token(token)
                self.lbl_info.configure(text="Ngrok Token Saved!", text_color="green")
            except Exception as e:
                self.lbl_info.configure(text=f"Error saving token: {e}", text_color="red")
        else:
            self.lbl_info.configure(text="Please enter a valid token.", text_color="orange")

    def toggle_server(self):
        if not self.is_running:
            self.start_server()
        else:
            self.lbl_info.configure(text="To stop fully, close the window.")
            self.btn_toggle.configure(state="disabled")

    def start_server(self):
        self.is_running = True
        self.lbl_status.configure(text="Status: RUNNING (Local)", text_color="green")
        self.btn_toggle.configure(text="Running...", fg_color="gray", state="disabled") 
        self.btn_online.configure(state="normal")
        
        self.btn_docs.configure(state="normal")
        self.btn_test.configure(state="normal")
        
        self.server_thread = threading.Thread(target=self.run_uvicorn, daemon=True)
        self.server_thread.start()

    def run_uvicorn(self):
        uvicorn.run(app, host="0.0.0.0", port=self.port, log_level="error", use_colors=False)

    def toggle_online(self):
        if not self.public_url:
            self.start_online()
        else:
            self.lbl_info.configure(text="Already online.")

    def start_online(self):
        self.btn_online.configure(text="Connecting...", state="disabled")
        self.lbl_info.configure(text="Initializing ngrok... please wait")
        threading.Thread(target=self._connect_ngrok, daemon=True).start()

    def _connect_ngrok(self):
        try:
            self.public_url = ngrok.connect(self.port).public_url
            self.lbl_status.configure(text=f"Status: ONLINE (Globally Accessible)", text_color="#3B8ED0")
            self.lbl_public.configure(text=f"Public URL: {self.public_url}", text_color="#3B8ED0", cursor="hand2")
            self.btn_online.configure(text="Online Active", fg_color="green")
            self.lbl_info.configure(text="Tunnel established! Use Public URL for n8n.")
        except Exception as e:
            self.lbl_info.configure(text=f"Ngrok Error: {str(e)[:50]}...", text_color="red")
            self.btn_online.configure(text="Go Online (ngrok)", state="normal", fg_color="#3B8ED0")
            print(f"Ngrok Detail Error: {e}")

    def open_browser(self, url):
        target = url if url else f"http://localhost:{self.port}"
        webbrowser.open(target)

    def open_docs(self):
        base = self.public_url if self.public_url else f"http://localhost:{self.port}"
        webbrowser.open(f"{base}/docs")

    def open_test(self):
        base = self.public_url if self.public_url else f"http://localhost:{self.port}"
        webbrowser.open(f"{base}/search?query=cats&limit=1")
    
    def open_github(self):
        webbrowser.open("https://github.com/expher510/YouTube_Shorts_API-and-Control_Panel")

if __name__ == "__main__":
    app_gui = APIApp()
    app_gui.mainloop()
