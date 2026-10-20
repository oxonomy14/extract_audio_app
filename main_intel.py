import os
import tempfile
import queue
import re
import shutil
import subprocess
import sys
import threading
import webbrowser
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse

import certifi
import yt_dlp
from yt_dlp.utils import DownloadCancelled


APP_NAME = "Extract Audio"
APP_VERSION = "0.2.0-beta.1"
BUILD_NUMBER = "Build 1"
APP_AUTHOR = "Andrii Semenenko"
HELP_FILENAME = "HELP.md"

VIDEO_FORMATS = "*.mp4 *.mov *.mkv *.avi *.webm *.m4v"
SUPPORTED_HOSTS = ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "vimeo.com", "www.vimeo.com", "player.vimeo.com")

def is_supported_url(value: str) -> bool:
    try:
        parsed = urlparse(value.strip())
        host = (parsed.hostname or "").lower()
        return parsed.scheme in ("http", "https") and any(
            host == item or host.endswith("." + item) for item in SUPPORTED_HOSTS
        )
    except ValueError:
        return False

def safe_filename(value: str) -> str:
    value = re.sub(r'[\\/:*?"<>|]+', "_", value).strip(" .")
    return value[:150] or "audio"


def parse_time(value: str) -> float:
    """Convert HH:MM:SS or MM:SS to seconds."""
    value = value.strip()
    if not value:
        raise ValueError("Введи время в формате ЧЧ:ММ:СС.")

    parts = value.split(":")
    if len(parts) not in (2, 3):
        raise ValueError(
            f"Некорректное время: {value}. Используй ЧЧ:ММ:СС или ММ:СС."
        )

    try:
        numbers = [float(part) for part in parts]
    except ValueError as error:
        raise ValueError(f"Некорректное время: {value}.") from error

    if any(number < 0 for number in numbers):
        raise ValueError("Время не может быть отрицательным.")

    if len(numbers) == 3:
        hours, minutes, seconds = numbers
        if minutes >= 60 or seconds >= 60:
            raise ValueError("Минуты и секунды должны быть меньше 60.")
        return hours * 3600 + minutes * 60 + seconds

    minutes, seconds = numbers
    if seconds >= 60:
        raise ValueError("Секунды должны быть меньше 60.")
    return minutes * 60 + seconds


def format_time(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class ExtractAudioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Extract Audio")
        self.root.geometry("760x680")
        self.root.minsize(640, 600)

        self.video_path = None
        self.process = None
        self.is_running = False
        self.events = queue.Queue()
        self.duration = None
        self.progress_duration = None
        self.last_logged_percent = -1
        self.cancel_requested = False
        self.diagnostic_text = ""
        self.output_path = None
        self.source_mode = tk.StringVar(value="file")
        self.source_url = tk.StringVar(value="")
        self.active_ytdlp = None
        self.temp_dir = None
        self.current_mode = "file"
        self.current_url = ""
        self.start_seconds = None
        self.end_seconds = None
        self.output_quality = "48"
        self._overwrite_decision_ready = True
        self._overwrite_allowed = False

        self.quality = tk.StringVar(value="48")
        self.file_label = tk.StringVar(value="Видео не выбрано")
        self.status = tk.StringVar(value="Готово к работе")
        self.progress_value = tk.DoubleVar(value=0)
        self.start_time = tk.StringVar(value="")
        self.end_time = tk.StringVar(value="")

        self._build_menu()
        self._build_ui()
        self.root.after(100, self._process_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_menu(self):
        """Build a simple macOS app menu without the system Help search menu."""
        menu_bar = tk.Menu(self.root)
        app_menu = tk.Menu(menu_bar, tearoff=False)
        app_menu.add_command(label="Справка", command=self._show_help)
        app_menu.add_command(label="О программе", command=self._show_about)
        app_menu.add_separator()
        app_menu.add_command(label="Выход", command=self._on_close)
        menu_bar.add_cascade(label="Файл", menu=app_menu)
        self.root.configure(menu=menu_bar)

    def _help_file_path(self):
        if getattr(sys, "frozen", False):
            return Path(sys._MEIPASS) / HELP_FILENAME
        return Path(__file__).resolve().with_name(HELP_FILENAME)

    def _show_help(self):
        help_path = self._help_file_path()
        try:
            help_text = help_path.read_text(encoding="utf-8")
        except OSError:
            help_text = (
                "Справка не найдена. Помести HELP.md рядом с приложением "
                "или включи его в сборку."
            )

        window = tk.Toplevel(self.root)
        window.title(f"Справка — {APP_NAME}")
        window.geometry("720x620")
        window.minsize(520, 400)
        window.transient(self.root)

        container = ttk.Frame(window, padding=12)
        container.pack(fill="both", expand=True)

        # Pack the bottom bar first so it remains visible while the text area
        # uses the remaining space and scrolls independently.
        button_bar = ttk.Frame(container)
        button_bar.pack(side="bottom", fill="x", pady=(10, 0))
        ttk.Button(
            button_bar,
            text="Закрыть",
            command=window.destroy,
        ).pack(side="right")

        text_frame = ttk.Frame(container)
        text_frame.pack(side="top", fill="both", expand=True)

        view = tk.Text(
            text_frame,
            wrap="word",
            font=("Helvetica", 11),
            padx=14,
            pady=12,
            spacing1=2,
            spacing3=4,
            relief="flat",
            borderwidth=0,
        )
        view.tag_configure(
            "title", font=("Helvetica", 18, "bold"), spacing1=8, spacing3=10
        )
        view.tag_configure(
            "heading", font=("Helvetica", 13, "bold"), spacing1=12, spacing3=5
        )
        view.tag_configure("bold", font=("Helvetica", 11, "bold"))
        view.tag_configure("list", lmargin1=20, lmargin2=36)
        scrollbar = ttk.Scrollbar(
            text_frame, orient="vertical", command=view.yview
        )
        view.configure(yscrollcommand=scrollbar.set)

        # Render the small subset of Markdown used by HELP.md.
        for line in help_text.splitlines():
            stripped = line.strip()
            if not stripped:
                view.insert("end", "\n")
                continue
            if stripped.startswith("# "):
                view.insert("end", stripped[2:] + "\n", "title")
                continue
            if stripped.startswith("## "):
                view.insert("end", stripped[3:] + "\n", "heading")
                continue
            if re.match(r"^\d+\.\s+", stripped):
                view.insert("end", stripped + "\n", "list")
                continue
            parts = re.split(r"(\*\*.*?\*\*)", stripped)
            for part in parts:
                if part.startswith("**") and part.endswith("**") and len(part) >= 4:
                    view.insert("end", part[2:-2], "bold")
                else:
                    view.insert("end", part)
            view.insert("end", "\n")

        view.configure(state="disabled")
        view.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        window.bind("<Escape>", lambda _event: window.destroy())
        window.protocol("WM_DELETE_WINDOW", window.destroy)

    def _show_about(self):
        window = tk.Toplevel(self.root)
        window.title("О программе")
        window.geometry("440x390")
        window.resizable(False, False)
        window.transient(self.root)

        content = ttk.Frame(window, padding=24)
        content.pack(fill="both", expand=True)

        ttk.Label(
            content,
            text=APP_NAME,
            font=("Helvetica", 20, "bold"),
        ).pack(pady=(0, 8))

        ttk.Label(
            content,
            text=f"Версия {APP_VERSION} · {BUILD_NUMBER}",
        ).pack(pady=(0, 8))

        # This release is built for Intel Macs only (x86_64).
        ttk.Label(
            content,
            text="Для Intel Mac (x86_64)",
            foreground="#1769aa",
            font=("Helvetica", 10, "bold"),
        ).pack(pady=(0, 14))

        ttk.Label(
            content,
            text="Инструмент для извлечения аудио из видео\nи подготовки записей к транскрибации.",
            justify="center",
            wraplength=360,
        ).pack(pady=(0, 14))

        ttk.Label(content, text=f"Автор: {APP_AUTHOR}").pack(pady=(0, 4))

        website = ttk.Label(
            content, text="andriiweb.dev", foreground="#1769aa", cursor="hand2"
        )
        website.pack(pady=(0, 3))
        website.bind("<Button-1>", lambda _event: webbrowser.open("https://andriiweb.dev"))

        email = ttk.Label(
            content, text="hello@andriiweb.dev", foreground="#1769aa", cursor="hand2"
        )
        email.pack(pady=(0, 8))
        email.bind("<Button-1>", lambda _event: webbrowser.open("mailto:hello@andriiweb.dev"))

        ttk.Label(content, text="© 2026 Andrii Semenenko").pack(pady=(0, 12))
        ttk.Button(content, text="Закрыть", command=window.destroy).pack()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)

        ttk.Label(
            main,
            text="Extract Audio",
            font=("Helvetica", 20, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            main,
            text="Извлечение аудио из видео для транскрибации",
        ).pack(anchor="w", pady=(2, 4))

        # Compatibility notice: this build targets Intel Macs only.
        ttk.Label(
            main,
            text="Версия для Intel Mac (x86_64)",
            foreground="#1769aa",
            font=("Helvetica", 10, "bold"),
        ).pack(anchor="w", pady=(0, 14))

        file_frame = ttk.LabelFrame(main, text="Источник видео", padding=10)
        file_frame.pack(fill="x", pady=(0, 10))

        ttk.Radiobutton(
            file_frame, text="Файл на компьютере", variable=self.source_mode,
            value="file", command=self._update_source_mode,
        ).pack(anchor="w")
        file_row = ttk.Frame(file_frame)
        file_row.pack(fill="x", pady=(4, 8))
        self.file_label_widget = ttk.Label(
            file_row, textvariable=self.file_label, wraplength=470
        )
        self.file_label_widget.pack(side="left", fill="x", expand=True)
        self.choose_button = ttk.Button(
            file_row, text="Выбрать видео", command=self._choose_video
        )
        self.choose_button.pack(side="right", padx=(8, 0))
        ttk.Separator(file_frame).pack(fill="x", pady=5)
        ttk.Radiobutton(
            file_frame, text="Ссылка на YouTube или Vimeo",
            variable=self.source_mode, value="url",
            command=self._update_source_mode,
        ).pack(anchor="w")
        self.url_entry = ttk.Entry(file_frame, textvariable=self.source_url)
        self.url_entry.pack(fill="x", pady=(5, 2))
        ttk.Label(
            file_frame,
            text="Работают доступные видео. Видео с ограничениями доступа могут не загрузиться.",
            foreground="gray", wraplength=690,
        ).pack(anchor="w")

        segment_frame = ttk.LabelFrame(
            main,
            text="Фрагмент аудио (необязательно)",
            padding=10,
        )
        segment_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(
            segment_frame,
            text=(
                "Оставь оба поля пустыми, чтобы извлечь всё аудио. "
                "Формат времени: ЧЧ:ММ:СС, например 00:35:00."
            ),
            foreground="gray",
            wraplength=690,
        ).pack(anchor="w", pady=(0, 8))

        time_row = ttk.Frame(segment_frame)
        time_row.pack(fill="x")

        ttk.Label(time_row, text="Начало:").pack(side="left")
        self.start_entry = ttk.Entry(
            time_row,
            textvariable=self.start_time,
            width=13,
        )
        self.start_entry.pack(side="left", padx=(6, 16))

        ttk.Label(time_row, text="Конец:").pack(side="left")
        self.end_entry = ttk.Entry(
            time_row,
            textvariable=self.end_time,
            width=13,
        )
        self.end_entry.pack(side="left", padx=6)

        quality_frame = ttk.LabelFrame(main, text="Качество MP3", padding=10)
        quality_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(quality_frame, text="Битрейт:").pack(side="left")

        self.quality_box = ttk.Combobox(
            quality_frame,
            textvariable=self.quality,
            values=["32", "48", "64", "96", "128", "192"],
            state="readonly",
            width=8,
        )
        self.quality_box.pack(side="left", padx=8)

        ttk.Label(
            quality_frame,
            text="кбит/с — для речи обычно достаточно 48–64",
        ).pack(side="left")

        controls = ttk.Frame(main)
        controls.pack(fill="x", pady=(0, 10))

        self.start_button = ttk.Button(
            controls,
            text="Извлечь аудио",
            command=self._start,
        )
        self.start_button.pack(side="left")

        self.cancel_button = ttk.Button(
            controls,
            text="Отменить",
            command=self._cancel,
            state="disabled",
        )
        self.cancel_button.pack(side="left", padx=8)

        ttk.Label(main, textvariable=self.status).pack(
            anchor="w", pady=(0, 5)
        )

        progress_frame = ttk.Frame(main)
        progress_frame.pack(fill="x", pady=(0, 10))

        self.progress = ttk.Progressbar(
            progress_frame,
            variable=self.progress_value,
            maximum=100,
            mode="determinate",
        )
        self.progress.pack(fill="x")

        self.progress_label = ttk.Label(
            progress_frame,
            text="0%",
            anchor="center",
        )
        self.progress_label.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(
            main,
            text="Журнал обработки",
            font=("Helvetica", 12, "bold"),
        ).pack(anchor="w", pady=(0, 5))

        log_frame = ttk.Frame(main)
        log_frame.pack(fill="both", expand=True)

        self.log = tk.Text(
            log_frame,
            height=10,
            wrap="word",
            font=("Menlo", 10),
            state="disabled",
            background="#171717",
            foreground="#eeeeee",
            insertbackground="#ffffff",
        )
        scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.log.yview,
        )
        self.log.configure(yscrollcommand=scrollbar.set)

        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _update_source_mode(self):
        if self.is_running:
            return
        is_file = self.source_mode.get() == "file"
        self.choose_button.configure(state="normal" if is_file else "disabled")
        self.url_entry.configure(state="disabled" if is_file else "normal")
        self.file_label_widget.configure(foreground="black" if is_file else "gray")

    def _write_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _choose_video(self):
        if self.is_running:
            return

        filename = filedialog.askopenfilename(
            parent=self.root,
            title="Выбери видео",
            filetypes=[
                ("Видеофайлы", VIDEO_FORMATS),
                ("Все файлы", "*.*"),
            ],
        )

        if filename:
            self.video_path = Path(filename)
            self.file_label.set(self.video_path.name)
            self.status.set("Видео выбрано")
            self._write_log(f"Выбрано видео: {self.video_path}")

    def _ffmpeg_path(self):
        if getattr(sys, "frozen", False):
            bundled_path = Path(sys._MEIPASS) / "ffmpeg"
            if bundled_path.is_file():
                return str(bundled_path)
            raise FileNotFoundError(
                "Не удалось запустить компонент обработки аудио. "
                "Переустановите приложение."
            )

        path = shutil.which("ffmpeg")
        if path:
            return path

        local_path = Path.home() / "bin" / "ffmpeg"
        if local_path.is_file():
            return str(local_path)

        raise FileNotFoundError(
            "FFmpeg не найден. Проверьте установку в режиме разработки."
        )

    def _make_output_path(self, start_seconds, end_seconds):
        if start_seconds is None:
            return self.video_path.with_suffix(".mp3")

        start_stamp = format_time(start_seconds).replace(":", "-")
        end_stamp = format_time(end_seconds).replace(":", "-")
        return self.video_path.with_name(
            f"{self.video_path.stem}_{start_stamp}_{end_stamp}.mp3"
        )

    def _start(self):
        if self.is_running:
            return

        mode = self.source_mode.get()
        url = self.source_url.get().strip()
        source_path = None
        if mode == "file":
            if not self.video_path:
                messagebox.showwarning("Нет видео", "Сначала выбери видеофайл.", parent=self.root)
                return
            if not self.video_path.is_file():
                messagebox.showerror("Ошибка", "Исходный видеофайл не найден.", parent=self.root)
                return
            source_path = self.video_path
        else:
            if not url:
                messagebox.showwarning("Нет ссылки", "Вставь ссылку на видео.", parent=self.root)
                return
            if not is_supported_url(url):
                messagebox.showwarning("Неподдерживаемая ссылка", "Вставь ссылку на YouTube или Vimeo.", parent=self.root)
                return

        start_text = self.start_time.get().strip()
        end_text = self.end_time.get().strip()
        if bool(start_text) != bool(end_text):
            messagebox.showwarning("Не указан интервал", "Укажи и начало, и конец фрагмента либо оставь оба поля пустыми.", parent=self.root)
            return
        start_seconds = end_seconds = None
        if start_text and end_text:
            try:
                start_seconds = parse_time(start_text)
                end_seconds = parse_time(end_text)
            except ValueError as error:
                messagebox.showwarning("Некорректное время", str(error), parent=self.root)
                return
            if end_seconds <= start_seconds:
                messagebox.showwarning("Некорректный интервал", "Время окончания должно быть позже времени начала.", parent=self.root)
                return

        output_path = self._make_output_path(start_seconds, end_seconds) if mode == "file" else None
        if output_path and output_path.exists():
            if not messagebox.askyesno("Файл уже существует", f"Файл уже существует:\n\n{output_path}\n\nПерезаписать его?", parent=self.root):
                return

        self.start_seconds = start_seconds
        self.end_seconds = end_seconds
        self.output_path = output_path
        self.current_mode = mode
        self.current_url = url
        self.output_quality = self.quality.get()
        self.is_running = True
        self.cancel_requested = False
        self.duration = None
        self.progress_duration = (
            end_seconds - start_seconds
            if start_seconds is not None
            else None
        )
        self.last_logged_percent = -1
        self.diagnostic_text = ""
        self.progress_value.set(0)
        self.progress_label.configure(text="0%")

        self.start_button.configure(state="disabled")
        self.choose_button.configure(state="disabled")
        self.url_entry.configure(state="disabled")
        self.quality_box.configure(state="disabled")
        self.start_entry.configure(state="disabled")
        self.end_entry.configure(state="disabled")
        self.cancel_button.configure(state="normal")

        self.status.set("Подготовка видео...")
        self._write_log("-" * 45)
        self._write_log("Подготовка...")
        self._write_log("Источник: локальный файл" if mode == "file" else f"Источник: {url}")
        self._write_log(f"Качество аудио: {self.output_quality} кбит/с")

        if start_seconds is not None:
            self._write_log(
                f"Фрагмент: {format_time(start_seconds)} — "
                f"{format_time(end_seconds)}"
            )
        else:
            self._write_log("Режим: всё аудио")

        worker = self._run_ffmpeg if mode == "file" else self._run_url
        threading.Thread(target=worker, daemon=True).start()

    def _certificate_path(self):
        if getattr(sys, "frozen", False):
            bundled = Path(sys._MEIPASS) / "cacert.pem"
            if bundled.is_file():
                return str(bundled)
        return certifi.where()

    def _run_url(self):
        try:
            cert_path = self._certificate_path()
            self.events.put(("status", "Загрузка аудиопотока..."))
            self.events.put(("log", "Подключение к источнику..."))
            with tempfile.TemporaryDirectory(prefix="extract_audio_") as temp_name:
                temp_folder = Path(temp_name)
                progress_state = {"last": -1}

                def progress_hook(data):
                    if self.cancel_requested:
                        raise DownloadCancelled("Загрузка отменена пользователем")
                    if data.get("status") == "downloading":
                        total = data.get("total_bytes") or data.get("total_bytes_estimate")
                        current = data.get("downloaded_bytes", 0)
                        if total:
                            percent = min(49, int(current / total * 50))
                            if percent != progress_state["last"]:
                                progress_state["last"] = percent
                                self.events.put(("progress_absolute", percent))
                            self.events.put(("status", f"Загрузка аудио: {current / total * 100:.1f}%"))
                    elif data.get("status") == "finished":
                        self.events.put(("log", "Аудиопоток загружен. Начинаю обработку..."))

                options = {
                    "format": "bestaudio/best",
                    "outtmpl": str(temp_folder / "source.%(ext)s"),
                    "noplaylist": True,
                    "quiet": True,
                    "no_warnings": False,
                    "progress_hooks": [progress_hook],
                    "retries": 3,
                    "socket_timeout": 30,
                    "nocheckcertificate": False,
                    "logger": _YtDlpLogger(self.events),
                    "cachedir": False,
                }
                # Keep SSL verification enabled and use certifi's trusted CA bundle.
                os.environ["SSL_CERT_FILE"] = cert_path
                os.environ["REQUESTS_CA_BUNDLE"] = cert_path
                with yt_dlp.YoutubeDL(options) as ydl:
                    self.active_ytdlp = ydl
                    info = ydl.extract_info(self.current_url, download=True)
                    downloaded = Path(ydl.prepare_filename(info))
                self.active_ytdlp = None
                if self.cancel_requested:
                    self.events.put(("cancelled", None))
                    return
                if not downloaded.is_file():
                    candidates = [f for f in temp_folder.iterdir() if f.is_file() and not f.name.endswith((".part", ".ytdl"))]
                    if not candidates:
                        raise FileNotFoundError("yt-dlp не создал файл аудиопотока.")
                    downloaded = candidates[0]

                title = safe_filename(info.get("title") or "audio")
                out_dir = Path.home() / "Downloads"
                if not out_dir.is_dir():
                    out_dir = Path.home()
                if self.start_seconds is None:
                    output_path = out_dir / f"{title}.mp3"
                else:
                    a = format_time(self.start_seconds).replace(":", "-")
                    b = format_time(self.end_seconds).replace(":", "-")
                    output_path = out_dir / f"{title}_{a}_{b}.mp3"

                if output_path.exists():
                    self._overwrite_decision_ready = False
                    self._overwrite_allowed = False
                    self.events.put(("output_exists", str(output_path)))
                    while not self.cancel_requested and not self._overwrite_decision_ready:
                        threading.Event().wait(0.1)
                    if self.cancel_requested or not self._overwrite_allowed:
                        self.events.put(("cancelled", None))
                        return

                self.output_path = output_path
                if self.cancel_requested:
                    self.events.put(("cancelled", None))
                    return
                self._run_ffmpeg(downloaded, output_path, progress_offset=50, progress_scale=50)
        except DownloadCancelled:
            self.events.put(("cancelled", None))
        except Exception as error:
            if self.cancel_requested:
                self.events.put(("cancelled", None))
            else:
                self.events.put(("error", f"Не удалось загрузить видео: {error}"))
        finally:
            self.active_ytdlp = None

    def _run_ffmpeg(self, source_path=None, output_path=None, progress_offset=0, progress_scale=100):
        process = None
        source_path = source_path or self.video_path
        output_path = output_path or self.output_path

        try:
            ffmpeg = self._ffmpeg_path()

            command = [
                ffmpeg,
                "-hide_banner",
                "-nostats",
                "-progress",
                "pipe:1",
            ]

            # Seek to the start before opening the source. This applies to
            # both local files and audio streams downloaded from a URL.
            if self.start_seconds is not None:
                command.extend(["-ss", str(self.start_seconds)])

            command.extend(["-i", str(source_path)])

            # -t is the fragment duration (end - start), not the end timestamp.
            if self.start_seconds is not None:
                command.extend(["-t", str(self.end_seconds - self.start_seconds)])

            command.extend(
                [
                    "-vn",
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    f"{self.output_quality}k",
                    "-y",
                    str(output_path),
                ]
            )

            self.events.put(("status", "Извлечение аудио..."))

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env={**os.environ, "SSL_CERT_FILE": self._certificate_path()},
            )
            self.process = process

            def read_stderr():
                duration_pattern = re.compile(
                    r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)"
                )
                diagnostic_lines = []

                for line in process.stderr:
                    match = duration_pattern.search(line)
                    if match:
                        hours, minutes, seconds = match.groups()
                        duration = (
                            int(hours) * 3600
                            + int(minutes) * 60
                            + float(seconds)
                        )
                        self.events.put(("duration", duration))

                    if re.search(
                        r"\b(error|invalid|failed|unable|no such file)\b",
                        line,
                        re.IGNORECASE,
                    ):
                        diagnostic_lines.append(line.rstrip())

                if diagnostic_lines:
                    self.events.put(("diagnostic", "\n".join(diagnostic_lines)))

            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stderr_thread.start()

            for line in process.stdout:
                line = line.strip()

                if line.startswith("out_time="):
                    timestamp = line.split("=", 1)[1]
                    try:
                        hours, minutes, seconds = timestamp.split(":")
                        elapsed = (
                            int(hours) * 3600
                            + int(minutes) * 60
                            + float(seconds)
                        )
                        duration = self.progress_duration or self.duration
                        if duration:
                            local_percent = min(99, int(elapsed / duration * 100))
                            percent = min(99, progress_offset + int(local_percent * progress_scale / 100))
                            self.events.put(("progress_absolute", percent))
                    except ValueError:
                        pass

                elif line == "progress=end":
                    self.events.put(("progress_end", None))

            return_code = process.wait()
            stderr_thread.join()

            if self.cancel_requested:
                self.events.put(("cancelled", None))
            elif return_code == 0:
                self.events.put(("done", str(output_path)))
            else:
                self.events.put(
                    (
                        "error",
                        "Не удалось обработать видео. "
                        "Проверь формат файла и временной интервал.",
                    )
                )

        except Exception as error:
            self.events.put(("error", str(error)))

        finally:
            self.process = None

    def _process_events(self):
        try:
            while True:
                event, value = self.events.get_nowait()

                if event == "log":
                    self._write_log(value)

                elif event == "status":
                    self.status.set(value)
                    if value == "Извлечение аудио...":
                        self._write_log(value)

                elif event == "duration":
                    self.duration = value
                    if self.progress_duration is None:
                        self.progress_duration = value

                elif event == "progress_absolute":
                    percent = int(value)
                    self.progress_value.set(percent)
                    self.progress_label.configure(text=f"{percent}%")
                    if percent != self.last_logged_percent:
                        self._write_log(f"Обработано {percent}%")
                        self.last_logged_percent = percent

                elif event == "progress_end":
                    self.status.set("Сохранение файла...")
                    self._write_log("Сохранение аудиофайла...")

                elif event == "diagnostic":
                    self.diagnostic_text = value

                elif event == "output_exists":
                    overwrite = messagebox.askyesno(
                        "Файл уже существует",
                        f"Файл уже существует:\n\n{value}\n\nПерезаписать его?",
                        parent=self.root,
                    )
                    self._overwrite_allowed = overwrite
                    self._overwrite_decision_ready = True
                    if not overwrite:
                        self.cancel_requested = True

                elif event == "done":
                    self._finish()
                    self.progress_value.set(100)
                    self.progress_label.configure(text="100%")
                    self.status.set("Готово!")
                    self._write_log("Готово! Аудио сохранено.")

                    messagebox.showinfo(
                        "Готово",
                        f"Аудио успешно сохранено:\n\n{value}",
                        parent=self.root,
                    )

                elif event == "error":
                    self._finish()
                    self.status.set("Не удалось обработать видео")
                    self._write_log("Не удалось обработать видео.")

                    details = getattr(self, "diagnostic_text", "")
                    if details:
                        show_details = messagebox.askyesno(
                            "Ошибка обработки",
                            f"{value}\n\nПоказать технические подробности?",
                            parent=self.root,
                        )
                        if show_details:
                            messagebox.showerror(
                                "Технические подробности",
                                details[:5000],
                                parent=self.root,
                            )
                    else:
                        messagebox.showerror(
                            "Ошибка",
                            value,
                            parent=self.root,
                        )

                elif event == "cancelled":
                    self._finish()
                    self.status.set("Обработка отменена")
                    self._write_log("Обработка отменена пользователем.")

        except queue.Empty:
            pass

        if self.root.winfo_exists():
            self.root.after(100, self._process_events)

    def _finish(self):
        self.is_running = False
        self.process = None

        self.start_button.configure(state="normal")
        self.choose_button.configure(state="normal")
        self.url_entry.configure(state="normal")
        self.quality_box.configure(state="readonly")
        self.start_entry.configure(state="normal")
        self.end_entry.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self._update_source_mode()

    def _cancel(self):
        if not self.is_running:
            return

        # Set the flag even while yt-dlp is downloading; FFmpeg may not have
        # started yet. The yt-dlp progress hook checks this flag.
        self.cancel_requested = True
        self.status.set("Отмена операции...")
        self._write_log("Запрошена отмена операции...")

        if self.process:
            try:
                self.process.terminate()
            except OSError:
                pass

        self.cancel_button.configure(state="disabled")

    def _on_close(self):
        self.cancel_requested = True
        if self.process and self.is_running:
            try:
                self.process.terminate()
            except OSError:
                pass
        self.root.destroy()


class _YtDlpLogger:
    def __init__(self, events):
        self.events = events

    def debug(self, message):
        if message and not message.startswith("[debug]"):
            self.events.put(("log", message))

    def warning(self, message):
        self.events.put(("log", f"Предупреждение: {message}"))

    def error(self, message):
        self.events.put(("log", f"Ошибка yt-dlp: {message}"))


def main():
    root = tk.Tk()
    ExtractAudioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
