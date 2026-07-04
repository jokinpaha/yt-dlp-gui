import tkinter as tk
from tkinter import scrolledtext, messagebox, Menu, Canvas, filedialog
from tkinter import ttk
import subprocess
import threading
import os
import sys
import requests
import re
import ctypes
from functools import partial
import http.server
import socketserver
import json

# --- SETTINGS: CONFIGURATION ---
GITHUB_OWNER = "yt-dlp" 
GITHUB_REPO = "yt-dlp"
EXE_NAME = "yt-dlp.exe"  
LOCAL_EXE_PATH = os.path.join("bin", "yt-dlp.exe")  
SETTINGS_FILE = "settings.json"
# --- ------------------------- ---

myappid = u'jokinpaha.ytdlpgui.gui.1'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.geometry("850x780")  
        self.root.iconbitmap('icons/yticon.ico')

        # Variables for dynamic UI text
        self.local_version_var = tk.StringVar(value=" local: ...")
        self.remote_version_var = tk.StringVar(value="latest: ...")
        self.status_var = tk.StringVar()
        
        self.download_percent_var = tk.StringVar(value="0%")
        self.process_percent_var = tk.StringVar(value="0%")
        self.done_status_var = tk.StringVar(value="")

        self.sub_fi_var = tk.BooleanVar(value=False)
        self.sub_en_var = tk.BooleanVar(value=False)
        
        self.download_path_var = tk.StringVar(value=self.load_settings())

        self.latest_release_info = {}
        self.update_available = False
        
        # Queue management and cancellation variables
        self.is_downloading = False
        self.current_process = None  # Stores the active yt-dlp process
        self.was_cancelled = False   # Flag to indicate if the download was intentionally cancelled

        self.setup_ui()
        self.run_startup_check()
        self.start_local_server()

    def load_settings(self):
        default_dir = os.path.join(os.getcwd(), "downloads")
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    saved_path = data.get("download_path", default_dir)
                    if saved_path: return saved_path
            except Exception: pass
        os.makedirs(default_dir, exist_ok=True)
        return default_dir

    def save_settings(self, path):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({"download_path": path}, f)
        except Exception as e:
            self.console_write(f"Error saving settings: {e}\n")

    def setup_ui(self):
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Top section: URL field and buttons
        top_frame = tk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 5))

        url_label = tk.Label(top_frame, text="URL:")
        url_label.pack(side=tk.LEFT, padx=(0, 5))

        self.url_entry = tk.Entry(top_frame, font=("Helvetica", 10))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        self.create_context_menu()

        self.paste_button = tk.Button(top_frame, text="Paste", command=self.paste_url, font=("Helvetica", 10))
        self.paste_button.pack(side=tk.LEFT, padx=(5, 2))

        self.clear_button = tk.Button(top_frame, text="Clear", command=self.clear_url, font=("Helvetica", 10))
        self.clear_button.pack(side=tk.LEFT, padx=(0, 5))

        self.download_button = tk.Button(top_frame, text="Add to Queue", command=self.add_url_from_entry, font=("Helvetica", 10, "bold"))
        self.download_button.pack(side=tk.LEFT)

        # Folder option (Save path)
        folder_frame = tk.Frame(main_frame)
        folder_frame.pack(fill=tk.X, pady=(0, 5))
        
        folder_label = tk.Label(folder_frame, text="Destination folder:")
        folder_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.folder_entry = tk.Entry(folder_frame, textvariable=self.download_path_var, font=("Helvetica", 10))
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        
        self.browse_button = tk.Button(folder_frame, text="Browse", command=self.browse_folder, font=("Helvetica", 10))
        self.browse_button.pack(side=tk.LEFT, padx=(5, 0))

        # Subtitle options
        sub_frame = tk.Frame(main_frame)
        sub_frame.pack(fill=tk.X, pady=(0, 10))
        
        sub_label = tk.Label(sub_frame, text="Subtitles:", font=("Helvetica", 9, "bold"))
        sub_label.pack(side=tk.LEFT, padx=(42, 10))
        self.sub_fi_check = tk.Checkbutton(sub_frame, text="Finnish", variable=self.sub_fi_var)
        self.sub_fi_check.pack(side=tk.LEFT, padx=5)
        self.sub_en_check = tk.Checkbutton(sub_frame, text="English", variable=self.sub_en_var)
        self.sub_en_check.pack(side=tk.LEFT, padx=5)

        # Download queue header and management buttons
        queue_header_frame = tk.Frame(main_frame)
        queue_header_frame.pack(fill=tk.X)
        
        queue_label = tk.Label(queue_header_frame, text="Download Queue:")
        queue_label.pack(side=tk.LEFT, anchor='w')
        
        # Queue and current download management buttons
        self.clear_queue_button = tk.Button(queue_header_frame, text="Clear Queue", command=self.clear_queue, font=("Helvetica", 9), fg="darkred")
        self.clear_queue_button.pack(side=tk.RIGHT, padx=2)
        
        self.cancel_current_button = tk.Button(queue_header_frame, text="Cancel Current Download", command=self.cancel_current_download, font=("Helvetica", 9, "bold"), fg="red", state=tk.DISABLED)
        self.cancel_current_button.pack(side=tk.RIGHT, padx=2)

        # Download queue (Listbox)
        self.queue_listbox = tk.Listbox(main_frame, height=4, font=("Helvetica", 10))
        self.queue_listbox.pack(fill=tk.X, pady=(0, 10))

        # Progress bars
        progress_container = tk.Frame(main_frame)
        progress_container.pack(fill=tk.X, pady=(0, 10))

        dl_frame = tk.Frame(progress_container)
        dl_frame.pack(fill=tk.X, pady=2)
        tk.Label(dl_frame, text="Download:", width=10, anchor="w").pack(side=tk.LEFT)
        self.dl_bar = ttk.Progressbar(dl_frame, orient="horizontal", mode="determinate", maximum=100)
        self.dl_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Label(dl_frame, textvariable=self.download_percent_var, width=6, anchor="e").pack(side=tk.LEFT)

        proc_frame = tk.Frame(progress_container)
        proc_frame.pack(fill=tk.X, pady=2)
        tk.Label(proc_frame, text="Processing:", width=10, anchor="w").pack(side=tk.LEFT)
        self.proc_bar = ttk.Progressbar(proc_frame, orient="horizontal", mode="determinate", maximum=100)
        self.proc_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Label(proc_frame, textvariable=self.process_percent_var, width=6, anchor="e").pack(side=tk.LEFT)
        
        status_msg_frame = tk.Frame(progress_container)
        status_msg_frame.pack(fill=tk.X)
        self.done_label = tk.Label(status_msg_frame, textvariable=self.done_status_var, font=("Helvetica", 10, "bold"), fg="#00aa00")
        self.done_label.pack(side=tk.RIGHT, padx=5)

        # Console output
        console_label = tk.Label(main_frame, text="Console Output:")
        console_label.pack(anchor='w')
        self.console = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, bg="black", fg="#4cff4c", font=("Consolas", 10))
        self.console.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.console_write("UI initialized.\n", clear=True)

        # Version information
        version_frame = tk.Frame(main_frame)
        version_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        self.status_indicator = Canvas(version_frame, width=12, height=12, highlightthickness=0)
        self.status_indicator.pack(side=tk.LEFT, pady=2, padx=(0, 5))
        
        status_label = tk.Label(version_frame, textvariable=self.status_var, font=("Helvetica", 10, "bold"))
        status_label.pack(side=tk.LEFT)

        tk.Label(version_frame, textvariable=self.local_version_var).pack(side=tk.LEFT, padx=10)
        tk.Label(version_frame, textvariable=self.remote_version_var).pack(side=tk.LEFT)

        self.update_button = tk.Button(version_frame, text="Update", command=self.start_update, font=("Helvetica", 10), state=tk.DISABLED)
        self.update_button.pack(side=tk.RIGHT)

    # --- UI Helper Functions ---
    def browse_folder(self):
        selected_dir = filedialog.askdirectory(initialdir=self.download_path_var.get(), title="Select Download Folder")
        if selected_dir:
            self.download_path_var.set(selected_dir)
            self.save_settings(selected_dir)

    def create_context_menu(self):
        context_menu = Menu(self.root, tearoff=0)
        context_menu.add_command(label="Paste", command=self.paste_url)
        self.url_entry.bind("<Button-3>", lambda e: context_menu.post(e.x_root, e.y_root))

    def update_status_indicator(self, color, text):
        self.status_indicator.delete("all")
        self.status_indicator.create_oval(2, 2, 12, 12, fill=color, outline=color)
        self.status_var.set(text)

    def console_write(self, text, clear=False):
        self.console.config(state=tk.NORMAL)
        if clear: self.console.delete('1.0', tk.END)
        self.console.insert(tk.END, text)
        self.console.see(tk.END)
        self.console.config(state=tk.DISABLED)

    def set_buttons_state(self, state):
        self.sub_fi_check.config(state=state)
        self.sub_en_check.config(state=state)
        if self.update_button.cget("text") == "Download":
            self.update_button.config(state=state)
        elif self.update_available:
            self.update_button.config(state=state)
        else:
            self.update_button.config(state=tk.DISABLED)

    def clear_url(self):
        self.url_entry.delete(0, tk.END)

    def paste_url(self):
        try:
            clipboard_content = self.root.selection_get(selection="CLIPBOARD", type="STRING")
            if clipboard_content:
                self.clear_url()
                self.url_entry.insert(0, clipboard_content.strip())
        except Exception: pass

    # --- Queue Management ---
    def add_url_from_entry(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Error", "Please enter a URL before continuing.")
            return
            
        if not os.path.exists(LOCAL_EXE_PATH):
            messagebox.showwarning("File Missing", "yt-dlp.exe not found! Please download it by clicking the 'Download' button below.")
            return

        self.add_to_queue(url)
        self.clear_url()

    def add_to_queue(self, url):
        if self.update_available:
            if messagebox.askyesno("Update Available", "A new version is available. Do you want to update the program before continuing?"):
                self.start_update()
                return

        self.queue_listbox.insert(tk.END, url)
        self.console_write(f"Added to queue: {url}\n")
        self.process_queue()

    def process_queue(self):
        if self.is_downloading:
            return 
        
        if self.queue_listbox.size() > 0:
            self.is_downloading = True
            self.cancel_current_button.config(state=tk.NORMAL)  
            url = self.queue_listbox.get(0)
            self.queue_listbox.delete(0)
            self.run_download_process(url)
        else:
            self.is_downloading = False
            self.cancel_current_button.config(state=tk.DISABLED)  
            self.set_buttons_state(tk.NORMAL)

    def clear_queue(self):
        """Clears pending downloads from the list."""
        if self.queue_listbox.size() > 0:
            self.queue_listbox.delete(0, tk.END)
            self.console_write("\nDownload queue cleared by user.\n")

    def cancel_current_download(self):
        """Forcefully stops the currently running download."""
        if self.is_downloading and self.current_process:
            if messagebox.askyesno("Cancel Download", "Are you sure you want to cancel the current video download?"):
                self.was_cancelled = True
                self.console_write("\n[CANCELLATION] Stopping download process, please wait...\n")
                
                try:
                    # In Windows, TASKKILL must be used so yt-dlp and its child processes (like ffmpeg) terminate together
                    subprocess.run(f"taskkill /F /T /PID {self.current_process.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    # Fallback if taskkill fails (e.g., Linux/Mac)
                    try:
                        self.current_process.terminate()
                    except: pass
                
                self.cancel_current_button.config(state=tk.DISABLED)

    # --- Local Server (For Firefox Extension) ---
    def start_local_server(self):
        class RequestHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format, *args): pass 
            def do_OPTIONS(self):
                self.send_response(200, "ok")
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
                self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
                self.end_headers()
            def do_POST(self):
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data)
                    url = data.get("url")
                    if url:
                        app.root.after(0, app.add_to_queue, url)
                        self.send_response(200)
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(b"OK")
                    else: self.send_response(400); self.end_headers()
                except Exception: self.send_response(500); self.end_headers()

        def run_server():
            with socketserver.TCPServer(("localhost", 5000), RequestHandler) as httpd:
                self.console_write("Browser extension listening server started on port 5000.\n")
                httpd.serve_forever()
        threading.Thread(target=run_server, daemon=True).start()

    # --- Update and Download Functions ---
    def run_startup_check(self):
        self.update_status_indicator("red", "Checking for updates, please wait...")
        threading.Thread(target=self.check_for_updates, daemon=True).start()

    def start_update(self):
        url = self.latest_release_info.get("download_url")
        if not url: return
        self.set_buttons_state(tk.DISABLED)
        
        if self.update_button.cget("text") == "Download":
            self.console_write(f"Downloading yt-dlp.exe from: {url}\n")
        else:
            self.console_write(f"Downloading update from: {url}\n")
            
        threading.Thread(target=self.download_and_replace, args=(url,), daemon=True).start()

    def check_for_updates(self):
        try:
            os.makedirs(os.path.dirname(LOCAL_EXE_PATH), exist_ok=True)
            
            local_ver = self.get_local_version()
            self.root.after(0, self.local_version_var.set, f"local: {local_ver}")
            
            self.latest_release_info = self.get_latest_github_info()
            remote_ver = self.latest_release_info.get("version", "Not found")
            self.root.after(0, self.remote_version_var.set, f"latest: {remote_ver}")
            
            status_text = "Could not check versions."
            self.update_available = False
            
            if local_ver == "Not found":
                status_text = "yt-dlp.exe missing! Available for download."
                self.root.after(0, self.update_button.config, {"text": "Download", "state": tk.NORMAL})
            elif remote_ver != "Not found":
                if local_ver != remote_ver:
                    status_text = "Update available!"
                    self.update_available = True
                    self.root.after(0, self.update_button.config, {"text": "Update", "state": tk.NORMAL})
                else:
                    status_text = "Program is up to date."
                    self.root.after(0, self.update_button.config, {"text": "Update", "state": tk.DISABLED})
            else:
                self.root.after(0, self.update_button.config, {"text": "Update", "state": tk.DISABLED})
            
            self.root.after(0, self.update_status_indicator, "green", status_text)
        except Exception:
            self.root.after(0, self.update_status_indicator, "red", "Update check failed.")

    def get_local_version(self):
        try:
            process = subprocess.run(
                f"\"{LOCAL_EXE_PATH}\" --version", 
                capture_output=True, text=True, check=True, shell=True, 
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            ver_str = process.stdout.strip()
            match = re.search(r'(\d+\.\d+(\.\d+)?)', ver_str)
            return match.group(1) if match else "Unknown format"
        except Exception: 
            return "Not found"

    def get_latest_github_info(self):
        api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            tag_name = data["tag_name"]
            dl_url = next((a["browser_download_url"] for a in data.get("assets", []) if a["name"] == EXE_NAME), None)
            return {"version": tag_name.lstrip('v'), "download_url": dl_url}
        except Exception: 
            return {}

    def download_and_replace(self, url):
        temp_filename = LOCAL_EXE_PATH + ".new"
        try:
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(temp_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
            
            is_fresh_download = not os.path.exists(LOCAL_EXE_PATH)
            
            os.replace(temp_filename, LOCAL_EXE_PATH)
            self.console_write("Operation successful!\n")
            
            if is_fresh_download:
                self.root.after(0, lambda: messagebox.showinfo("Download Complete", "yt-dlp.exe downloaded successfully!\nThe program is now ready for use."))
                self.root.after(0, lambda: self.update_button.config(text="Update"))
                self.root.after(100, self.run_startup_check)
            else:
                if messagebox.askyesno("Update Complete", "yt-dlp has been updated successfully!\nDo you want to restart the program now?"):
                    self.console_write("Restarting...\n")
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                else:
                    self.console_write("The new version will be used upon the next launch.\n")
                    self.root.after(100, self.run_startup_check)
        except Exception as e:
            self.console_write(f"Error: {e}\n")
            if os.path.exists(temp_filename): os.remove(temp_filename)
        finally:
            self.root.after(0, self.set_buttons_state, tk.NORMAL)

    # --- Command Execution via Queue ---
    def run_download_process(self, url):
        self.set_buttons_state(tk.DISABLED)
        self.was_cancelled = False  
        
        self.dl_bar["value"] = 0
        self.proc_bar["value"] = 0
        self.download_percent_var.set("0%")
        self.process_percent_var.set("0%")
        self.done_status_var.set(f"Downloading: {url[:40]}...") 
        
        dl_path = self.download_path_var.get()
        if not os.path.exists(dl_path):
            os.makedirs(dl_path, exist_ok=True)
            
        command = f"\"{LOCAL_EXE_PATH}\" \"{url}\" --cookies-from-browser firefox -P \"{dl_path}\""
        
        selected_langs = []
        if self.sub_fi_var.get(): selected_langs.append("fi")
        if self.sub_en_var.get(): selected_langs.append("en")
            
        if selected_langs:
            langs_str = ",".join(selected_langs)
            command += f" --write-subs --write-auto-subs --sub-langs \"{langs_str}\" --convert-subs srt"
        
        self.console_write(f"Running command: {command}\n" + "="*40 + "\n")
        threading.Thread(target=self.run_command_in_thread, args=(command,), daemon=True).start()

    def run_command_in_thread(self, command):
        try:
            self.current_process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                shell=True, encoding='utf-8', errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            progress_regex = re.compile(r'(\d+\.\d+|\d+)%')

            for line in iter(self.current_process.stdout.readline, ''):
                if line:
                    self.root.after(0, partial(self.console_write, line))
                    is_download = "[download]" in line
                    is_processing = "[ExtractAudio]" in line or "[Merger]" in line or "[VideoConvertor]" in line
                    
                    match = progress_regex.search(line)
                    if match:
                        try:
                            percent_value = float(match.group(1))
                            if is_download:
                                self.root.after(0, self.update_dl_progress, percent_value)
                            elif is_processing:
                                self.root.after(0, self.update_proc_progress, percent_value)
                        except ValueError: pass
                            
            self.current_process.stdout.close()
            self.current_process.wait()
            
            if self.was_cancelled:
                self.root.after(0, self.done_status_var.set, "✕ Download cancelled by user.")
                self.root.after(0, self.download_percent_var.set, "0%")
                self.root.after(0, self.process_percent_var.set, "0%")
            elif self.current_process.returncode == 0:
                self.root.after(0, self.update_dl_progress, 100)
                self.root.after(0, self.update_proc_progress, 100)
                self.root.after(0, self.done_status_var.set, "✓ Done! All files cleaned up.")
                
            self.root.after(0, partial(self.console_write, f"\nCommand executed (exit code: {self.current_process.returncode}).\n"))
        except Exception as e:
            self.root.after(0, partial(self.console_write, f"\nError executing command: {e}\n"))
        finally:
            self.current_process = None
            self.is_downloading = False
            self.root.after(1000, self.process_queue)

    def update_dl_progress(self, value):
        self.dl_bar["value"] = value
        self.download_percent_var.set(f"{int(value)}%")

    def update_proc_progress(self, value):
        self.proc_bar["value"] = value
        self.process_percent_var.set(f"{int(value)}%")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
