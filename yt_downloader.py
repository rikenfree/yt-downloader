import customtkinter as ctk
from tkinter import filedialog
import yt_dlp
import threading
import os

try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG_PATH = None

# Configurations
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

RESOLUTIONS = {
    "Audio only (mp3)": ("8", "bestaudio/best", True),
    "360p": ("1", "bestvideo[height<=360]+bestaudio/best[height<=360]", False),
    "480p": ("2", "bestvideo[height<=480]+bestaudio/best[height<=480]", False),
    "720p": ("3", "bestvideo[height<=720]+bestaudio/best[height<=720]", False),
    "1080p": ("4", "bestvideo[height<=1080]+bestaudio/best[height<=1080]", False),
    "1440p": ("5", "bestvideo[height<=1440]+bestaudio/best[height<=1440]", False),
    "4K": ("6", "bestvideo[height<=2160]+bestaudio/best[height<=2160]", False),
    "Best available": ("7", "bestvideo+bestaudio/best", False),
}

class PauseDownloadException(Exception):
    pass

class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Video & Channel Downloader")
        self.geometry("850x650")
        self.minsize(750, 600)

        # State Variables
        self.is_downloading = False
        self.is_paused = False
        self.video_queue = [] # Will hold raw info dicts
        self.video_rows = [] # Will hold GUI elements dicts
        self.current_download_index = -1

        # Main Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Video list expands
        self.grid_rowconfigure(5, weight=1) # Console expands
        
        # 1. URL Input & Fetch
        self.url_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.url_frame.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="ew")
        self.url_frame.grid_columnconfigure(0, weight=1)

        self.url_label = ctk.CTkLabel(self.url_frame, text="YouTube URL (Video, Playlist, Channel, Shorts):", font=("Inter", 14, "bold"))
        self.url_label.grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky="w")
        
        self.url_entry = ctk.CTkEntry(self.url_frame, placeholder_text="Paste your link here...", height=40)
        self.url_entry.grid(row=1, column=0, padx=(0, 10), sticky="ew")
        
        self.fetch_btn = ctk.CTkButton(self.url_frame, text="Fetch Info", width=120, height=40, font=("Inter", 13, "bold"), command=self.start_fetch)
        self.fetch_btn.grid(row=1, column=1, sticky="e")

        # 2. List Controls
        self.list_controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.list_controls_frame.grid(row=1, column=0, padx=20, pady=(5, 5), sticky="ew")
        
        self.select_all_btn = ctk.CTkButton(self.list_controls_frame, text="Select All", width=100, height=30, command=self.select_all_videos)
        self.select_all_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.deselect_all_btn = ctk.CTkButton(self.list_controls_frame, text="Deselect All", width=100, height=30, command=self.deselect_all_videos)
        self.deselect_all_btn.grid(row=0, column=1)

        # 3. Video List Frame
        self.video_list_frame = ctk.CTkScrollableFrame(self, height=200)
        self.video_list_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="nsew")
        self.video_list_frame.grid_columnconfigure(1, weight=1)

        # 4. Path & Format Options
        self.options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.options_frame.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        self.options_frame.grid_columnconfigure(1, weight=1)

        self.format_label = ctk.CTkLabel(self.options_frame, text="Resolution / Format:", font=("Inter", 12))
        self.format_label.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="w")

        self.format_var = ctk.StringVar(value="1080p")
        self.format_dropdown = ctk.CTkOptionMenu(self.options_frame, values=list(RESOLUTIONS.keys()), variable=self.format_var)
        self.format_dropdown.grid(row=0, column=1, padx=0, pady=0, sticky="w")

        self.path_label = ctk.CTkLabel(self.options_frame, text="Save To:", font=("Inter", 12))
        self.path_label.grid(row=1, column=0, padx=(0, 10), pady=(15, 0), sticky="w")

        self.save_path = ctk.StringVar(value=os.getcwd())
        self.path_entry = ctk.CTkEntry(self.options_frame, textvariable=self.save_path, state="disabled")
        self.path_entry.grid(row=1, column=1, padx=(0, 10), pady=(15, 0), sticky="ew")

        self.browse_btn = ctk.CTkButton(self.options_frame, text="Browse", width=80, command=self.browse_folder)
        self.browse_btn.grid(row=1, column=2, padx=0, pady=(15, 0), sticky="e")

        # 5. Action Buttons
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=4, column=0, padx=20, pady=15, sticky="ew")
        self.action_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.download_btn = ctk.CTkButton(self.action_frame, text="Start Download", font=("Inter", 14, "bold"), height=40, command=self.start_download)
        self.download_btn.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.pause_btn = ctk.CTkButton(self.action_frame, text="Pause", font=("Inter", 14, "bold"), height=40, state="disabled", command=self.pause_download)
        self.pause_btn.grid(row=0, column=1, padx=10, sticky="ew")

        self.resume_btn = ctk.CTkButton(self.action_frame, text="Resume", font=("Inter", 14, "bold"), height=40, state="disabled", command=self.resume_download)
        self.resume_btn.grid(row=0, column=2, padx=(10, 0), sticky="ew")

        # 6. Log Output
        self.console_textbox = ctk.CTkTextbox(self, state="disabled", font=("Consolas", 12))
        self.console_textbox.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="nsew")

    def select_all_videos(self):
        for row in self.video_rows:
            row['var'].set(1)

    def deselect_all_videos(self):
        for row in self.video_rows:
            row['var'].set(0)

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.save_path.get())
        if folder:
            self.save_path.set(folder)

    def log_message(self, message):
        self.console_textbox.configure(state="normal")
        self.console_textbox.insert("end", message + "\n")
        self.console_textbox.see("end")
        self.console_textbox.configure(state="disabled")

    # --- FETCH LOGIC ---
    def start_fetch(self):
        url = self.url_entry.get().strip()
        if not url:
            self.log_message("ERROR: Please enter a YouTube URL.")
            return

        self.fetch_btn.configure(text="Fetching...", state="disabled")
        self.console_textbox.configure(state="normal")
        self.console_textbox.delete("1.0", "end")
        self.console_textbox.configure(state="disabled")
        self.log_message(f"Fetching info for: {url}...")
        
        # Clear existing list
        for row in self.video_rows:
            row['checkbox'].destroy()
            row['title_label'].destroy()
            row['progress'].destroy()
            row['status_label'].destroy()
        self.video_rows.clear()
        self.video_queue.clear()
        
        thread = threading.Thread(target=self.fetch_worker, args=(url,))
        thread.daemon = True
        thread.start()

    def fetch_worker(self, url):
        ydl_opts = {
            "extract_flat": True,
            "quiet": True,
            "no_warnings": True,
            "remote_components": ["ejs:github"],
            "js_runtimes": {"node": {}}
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            
            # Could be a single video or a playlist
            if 'entries' in info:
                entries = info['entries']
            else:
                entries = [info]
                
            valid_entries = [e for e in entries if e and (e.get('url') or e.get('id'))]
            self.after(0, self.populate_list, valid_entries)
        except Exception as e:
            self.after(0, self.log_message, f"ERROR fetching info: {str(e)}")
            self.after(0, lambda: self.fetch_btn.configure(text="Fetch Info", state="normal"))

    def populate_list(self, entries):
        self.video_queue = entries
        for i, entry in enumerate(entries):
            # Resolve url
            vid_url = entry.get('url')
            if not vid_url:
                vid_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                
            title = entry.get('title', f"Video {i+1}")
            
            var = ctk.IntVar(value=1)
            cb = ctk.CTkCheckBox(self.video_list_frame, text="", variable=var, width=30)
            cb.grid(row=i, column=0, padx=(5, 5), pady=5, sticky="w")
            
            title_label = ctk.CTkLabel(self.video_list_frame, text=title[:60] + ("..." if len(title) > 60 else ""), font=("Inter", 12))
            title_label.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            
            pb = ctk.CTkProgressBar(self.video_list_frame, width=150, height=10)
            pb.set(0)
            pb.grid(row=i, column=2, padx=10, pady=5, sticky="e")
            
            status_label = ctk.CTkLabel(self.video_list_frame, text="Pending", width=180, font=("Inter", 12), anchor="e")
            status_label.grid(row=i, column=3, padx=5, pady=5, sticky="e")
            
            self.video_rows.append({
                'index': i,
                'url': vid_url,
                'title': title,
                'var': var,
                'checkbox': cb,
                'title_label': title_label,
                'progress': pb,
                'status_label': status_label,
                'status': 'Pending' # Pending, Downloading, Paused, Completed, Error
            })

        self.log_message(f"Found {len(entries)} item(s).")
        self.fetch_btn.configure(text="Fetch Info", state="normal")
        self.current_download_index = -1

    # --- DOWNLOAD LOGIC ---
    def start_download(self):
        if not self.video_rows:
            self.log_message("ERROR: Please fetch a valid URL first.")
            return
            
        if self.is_downloading:
            return

        # Start from beginning if all were previously completed
        if self.current_download_index == -1:
            self.current_download_index = 0

        self._begin_download_thread()

    def pause_download(self):
        self.is_paused = True
        self.log_message("Pausing download... (will stop after current chunk)")
        self.pause_btn.configure(state="disabled")

    def resume_download(self):
        if self.is_downloading and not self.is_paused:
            return
        
        self.log_message("Resuming download sequence...")
        self.is_paused = False
        self._begin_download_thread()

    def _begin_download_thread(self):
        self.is_downloading = True
        self.is_paused = False
        
        self.download_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal")
        self.resume_btn.configure(state="disabled")
        self.fetch_btn.configure(state="disabled")
        
        format_key = self.format_var.get()
        _, fmt_code, audio_only = RESOLUTIONS[format_key]
        output_folder = self.save_path.get()
        
        thread = threading.Thread(target=self.download_queue_worker, args=(fmt_code, audio_only, output_folder))
        thread.daemon = True
        thread.start()

    def download_queue_worker(self, fmt, audio_only, output_folder):
        total_items = len(self.video_rows)
        
        while self.current_download_index < total_items:
            if self.is_paused:
                self.after(0, self.handle_paused_state)
                return
                
            row = self.video_rows[self.current_download_index]
            
            # Skip if unchecked
            if row['var'].get() == 0:
                self.current_download_index += 1
                continue
                
            # Skip if already completed
            if row['status'] == 'Completed':
                self.current_download_index += 1
                continue

            # Update UI for current item
            self.after(0, self.update_row_state, self.current_download_index, 'Downloading', 0.0)
            self.log_message(f"Starting: {row['title']}")

            output_template = os.path.join(output_folder, "%(title)s.%(ext)s")

            ydl_opts = {
                "format": fmt,
                "outtmpl": output_template,
                "merge_output_format": "mp4",
                "progress_hooks": [self._make_progress_hook(self.current_download_index)],
                "quiet": False,
                "no_warnings": False,
                "no_color": True,
                "logger": self.MyLogger(self.print_log),
                "js_runtimes": {"node": {}},
                "remote_components": ["ejs:github"]
            }

            if globals().get("FFMPEG_PATH"):
                ydl_opts["ffmpeg_location"] = globals().get("FFMPEG_PATH")

            if audio_only:
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
                ydl_opts["merge_output_format"] = None

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([row['url']])
                
                # Check if paused threw us out during this video
                if self.is_paused:
                    self.after(0, self.update_row_state, self.current_download_index, 'Paused', None)
                    self.after(0, self.handle_paused_state)
                    return
                else:
                    self.after(0, self.update_row_state, self.current_download_index, 'Completed', 1.0)
                    self.current_download_index += 1
                    
            except PauseDownloadException:
                # Naturally thrown from the hook
                self.after(0, self.update_row_state, self.current_download_index, 'Paused', None)
                self.after(0, self.handle_paused_state)
                return
            except Exception as e:
                self.after(0, self.log_message, f"FAILED: {row['title']} - {str(e)}")
                self.after(0, self.update_row_state, self.current_download_index, 'Error', None)
                self.current_download_index += 1

        # Finished queue
        self.after(0, self.handle_finished_state)

    def handle_paused_state(self):
        self.is_downloading = False
        self.download_btn.configure(state="disabled")
        self.resume_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled")
        self.fetch_btn.configure(state="disabled")
        self.log_message("Queue Paused. Click Resume to continue.")

    def handle_finished_state(self):
        self.is_downloading = False
        self.current_download_index = -1 # Reset for next run
        self.download_btn.configure(state="normal")
        self.resume_btn.configure(state="disabled")
        self.pause_btn.configure(state="disabled")
        self.fetch_btn.configure(state="normal")
        self.log_message("\nSUCCESS: Download queue finished!")

    def update_row_state(self, idx, status, progress_val=None, status_color=None):
        if idx >= len(self.video_rows):
            return
        row = self.video_rows[idx]
        row['status'] = status
        
        status_colors = {
            'Pending': 'gray',
            'Downloading': 'orange',
            'Processing...': 'orange',
            'Completed': 'green',
            'Paused': 'yellow',
            'Error': 'red'
        }
        
        color_to_use = status_color if status_color else status_colors.get(status, 'white')
        row['status_label'].configure(text=status, text_color=color_to_use)
        if progress_val is not None:
            row['progress'].set(progress_val)

    def _make_progress_hook(self, idx):
        def hook(d):
            if self.is_paused:
                raise PauseDownloadException("Download paused by user.")
                
            if d['status'] == 'downloading':
                try:
                    percent_str = d.get('_percent_str', '0.0%').strip()
                    percent_clean = percent_str.replace('%', '').replace('\x1b[0;94m', '').replace('\x1b[0m', '') # Fallback ansi clear
                    try:
                        percent_val = float(percent_clean) / 100.0
                    except ValueError:
                        percent_val = 0.0
                    
                    speed_str = d.get('_speed_str', 'N/A').strip()
                    eta_str = d.get('_eta_str', 'N/A').strip()
                    
                    status_text = f"{percent_str} ({speed_str} | ETA: {eta_str})"
                    # Custom yellow/orange output while actively downloading
                    self.after(0, self.update_row_state, idx, status_text, percent_val, 'orange')
                except Exception:
                    pass
            elif d['status'] == 'finished':
                self.after(0, self.update_row_state, idx, 'Processing...', 1.0, 'orange')
        return hook

    def print_log(self, msg):
        self.after(0, self.log_message, str(msg))

    class MyLogger(object):
        def __init__(self, log_callback):
            self.log_callback = log_callback
            self.last_msg = ""
            
        def debug(self, msg):
            if not msg.startswith('\r') and not msg.startswith('[download]   '):
                if msg.startswith('[download]') or msg.startswith('[ExtractAudio]') or msg.startswith('[Merger]'):
                    if msg != self.last_msg:
                        self.log_callback(msg)
                        self.last_msg = msg
        def warning(self, msg):
            pass # Suppress overly verbose warnings in queue mode
        def error(self, msg):
            self.log_callback(f"ERROR: {msg}")

if __name__ == "__main__":
    app = YouTubeDownloaderApp()
    app.mainloop()
