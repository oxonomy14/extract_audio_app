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
HELP_FILES = {"uk": "HELP_uk.md", "ru": "HELP_ru.md", "en": "HELP_en.md"}

def detect_language():
    """Use macOS preferred language; fall back to English."""
    try:
        result = subprocess.run(
            ["/usr/bin/defaults", "read", "-g", "AppleLanguages"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        raw = result.stdout.lower()
        if "uk" in raw or "uk_ua" in raw or "uk-ua" in raw:
            return "uk"
        if "ru" in raw or "ru_ru" in raw or "ru-ru" in raw:
            return "ru"
    except (OSError, subprocess.SubprocessError):
        pass
    return "en"

LANGUAGE = detect_language()
TRANSLATIONS = {'uk': {'menu_help': 'Довідка', 'menu_about': 'Про програму', 'menu_exit': 'Вийти', 'help_missing': 'Довідку не знайдено. Розмістіть HELP_uk.md поруч із застосунком або додайте файл до збірки.', 'close': 'Закрити', 'about_title': 'Про програму', 'version': 'Версія', 'architecture_arm': 'Для Mac з Apple Silicon (arm64)', 'architecture_intel': 'Для Intel Mac (x86_64)', 'description': 'Інструмент для вилучення аудіо з відео\nта підготовки записів до транскрибування.', 'author': 'Автор', 'subtitle': 'Вилучення аудіо з відео для транскрибування', 'source_video': 'Джерело відео', 'local_file': 'Файл на комп’ютері', 'choose_video': 'Вибрати відео', 'youtube_vimeo': 'Посилання на YouTube або Vimeo', 'url_note': 'Доступні відео можна завантажити. Відео з обмеженим доступом можуть бути недоступні.', 'segment': 'Фрагмент аудіо (необов’язково)', 'segment_note': 'Залиште обидва поля порожніми, щоб вилучити все аудіо. Формат часу: ГГ:ХХ:СС, наприклад 00:35:00.', 'start': 'Початок:', 'end': 'Кінець:', 'quality': 'Якість MP3', 'bitrate': 'Бітрейт:', 'kbps_note': 'кбіт/с — для мовлення зазвичай достатньо 48–64', 'extract': 'Вилучити аудіо', 'cancel': 'Скасувати', 'log': 'Журнал обробки', 'video_none': 'Відео не вибрано', 'ready': 'Готово до роботи', 'choose_video_title': 'Виберіть відео', 'video_files': 'Відеофайли', 'all_files': 'Усі файли', 'video_selected': 'Відео вибрано', 'selected_video': 'Вибрано відео:', 'no_video_title': 'Немає відео', 'choose_first': 'Спочатку виберіть відеофайл.', 'error': 'Помилка', 'source_missing': 'Вихідний відеофайл не знайдено.', 'no_url_title': 'Немає посилання', 'paste_url': 'Вставте посилання на відео.', 'unsupported_url': 'Посилання не підтримується', 'paste_supported_url': 'Вставте посилання на YouTube або Vimeo.', 'interval_missing': 'Не вказано інтервал', 'interval_both': 'Укажіть початок і кінець фрагмента або залиште обидва поля порожніми.', 'invalid_time': 'Некоректний час', 'invalid_interval': 'Некоректний інтервал', 'end_after_start': 'Час завершення має бути пізніше часу початку.', 'file_exists': 'Файл уже існує', 'overwrite': 'Файл уже існує:\n\n{path}\n\nПерезаписати його?', 'prepare': 'Підготовка відео...', 'preparing': 'Підготовка...', 'source_local': 'Джерело: локальний файл', 'source_url': 'Джерело: {url}', 'audio_quality': 'Якість аудіо: {quality} кбіт/с', 'fragment': 'Фрагмент: {start} — {end}', 'all_audio': 'Режим: усе аудіо', 'downloading_stream': 'Завантаження аудіопотоку...', 'connecting': 'Підключення до джерела...', 'download_percent': 'Завантаження аудіо: {percent:.1f}%', 'stream_downloaded': 'Аудіопотік завантажено. Починаю обробку...', 'yt_no_file': 'yt-dlp не створив файл аудіопотоку.', 'download_failed': 'Не вдалося завантажити відео: {error}', 'ffmpeg_missing_frozen': 'Не вдалося запустити компонент обробки аудіо. Перевстановіть застосунок.', 'ffmpeg_missing_dev': 'FFmpeg не знайдено. Перевірте встановлення в режимі розробки.', 'extracting': 'Вилучення аудіо...', 'save_file': 'Збереження файлу...', 'saving_audio': 'Збереження аудіофайлу...', 'done': 'Готово!', 'saved': 'Готово! Аудіо збережено.', 'success': 'Аудіо успішно збережено:\n\n{path}', 'processing_failed': 'Не вдалося обробити відео', 'processing_failed_log': 'Не вдалося обробити відео.', 'processing_error': 'Помилка обробки', 'technical_details': 'Показати технічні подробиці?', 'technical_title': 'Технічні подробиці', 'cancelled': 'Обробку скасовано', 'cancelled_log': 'Обробку скасовано користувачем.', 'cancel_request': 'Скасування операції...', 'cancel_requested_log': 'Надіслано запит на скасування операції...', 'warning': 'Попередження', 'time_format': 'Введіть час у форматі ГГ:ХХ:СС.', 'invalid_time_value': 'Некоректний час: {value}. Використовуйте ГГ:ХХ:СС або ХХ:СС.', 'invalid_time_short': 'Некоректний час: {value}.', 'negative_time': 'Час не може бути від’ємним.', 'minutes_seconds': 'Хвилини та секунди мають бути меншими за 60.', 'seconds_less': 'Секунди мають бути меншими за 60.', 'overwrite_warning': 'Попередження: {message}', 'yt_error': 'Помилка yt-dlp: {message}'}, 'ru': {'menu_help': 'Справка', 'menu_about': 'О программе', 'menu_exit': 'Выход', 'help_missing': 'Справка не найдена. Поместите HELP_ru.md рядом с приложением или включите файл в сборку.', 'close': 'Закрыть', 'about_title': 'О программе', 'version': 'Версия', 'architecture_arm': 'Для Mac с Apple Silicon (arm64)', 'architecture_intel': 'Для Intel Mac (x86_64)', 'description': 'Инструмент для извлечения аудио из видео\nи подготовки записей к транскрибации.', 'author': 'Автор', 'subtitle': 'Извлечение аудио из видео для транскрибации', 'source_video': 'Источник видео', 'local_file': 'Файл на компьютере', 'choose_video': 'Выбрать видео', 'youtube_vimeo': 'Ссылка на YouTube или Vimeo', 'url_note': 'Работают доступные видео. Видео с ограничениями доступа могут не загрузиться.', 'segment': 'Фрагмент аудио (необязательно)', 'segment_note': 'Оставь оба поля пустыми, чтобы извлечь всё аудио. Формат времени: ЧЧ:ММ:СС, например 00:35:00.', 'start': 'Начало:', 'end': 'Конец:', 'quality': 'Качество MP3', 'bitrate': 'Битрейт:', 'kbps_note': 'кбит/с — для речи обычно достаточно 48–64', 'extract': 'Извлечь аудио', 'cancel': 'Отменить', 'log': 'Журнал обработки', 'video_none': 'Видео не выбрано', 'ready': 'Готово к работе', 'choose_video_title': 'Выбери видео', 'video_files': 'Видеофайлы', 'all_files': 'Все файлы', 'video_selected': 'Видео выбрано', 'selected_video': 'Выбрано видео:', 'no_video_title': 'Нет видео', 'choose_first': 'Сначала выбери видеофайл.', 'error': 'Ошибка', 'source_missing': 'Исходный видеофайл не найден.', 'no_url_title': 'Нет ссылки', 'paste_url': 'Вставь ссылку на видео.', 'unsupported_url': 'Неподдерживаемая ссылка', 'paste_supported_url': 'Вставь ссылку на YouTube или Vimeo.', 'interval_missing': 'Не указан интервал', 'interval_both': 'Укажи и начало, и конец фрагмента либо оставь оба поля пустыми.', 'invalid_time': 'Некорректное время', 'invalid_interval': 'Некорректный интервал', 'end_after_start': 'Время окончания должно быть позже времени начала.', 'file_exists': 'Файл уже существует', 'overwrite': 'Файл уже существует:\n\n{path}\n\nПерезаписать его?', 'prepare': 'Подготовка видео...', 'preparing': 'Подготовка...', 'source_local': 'Источник: локальный файл', 'source_url': 'Источник: {url}', 'audio_quality': 'Качество аудио: {quality} кбит/с', 'fragment': 'Фрагмент: {start} — {end}', 'all_audio': 'Режим: всё аудио', 'downloading_stream': 'Загрузка аудиопотока...', 'connecting': 'Подключение к источнику...', 'download_percent': 'Загрузка аудио: {percent:.1f}%', 'stream_downloaded': 'Аудиопоток загружен. Начинаю обработку...', 'yt_no_file': 'yt-dlp не создал файл аудиопотока.', 'download_failed': 'Не удалось загрузить видео: {error}', 'ffmpeg_missing_frozen': 'Не удалось запустить компонент обработки аудио. Переустановите приложение.', 'ffmpeg_missing_dev': 'FFmpeg не найден. Проверьте установку в режиме разработки.', 'extracting': 'Извлечение аудио...', 'save_file': 'Сохранение файла...', 'saving_audio': 'Сохранение аудиофайла...', 'done': 'Готово!', 'saved': 'Готово! Аудио сохранено.', 'success': 'Аудио успешно сохранено:\n\n{path}', 'processing_failed': 'Не удалось обработать видео', 'processing_failed_log': 'Не удалось обработать видео.', 'processing_error': 'Ошибка обработки', 'technical_details': 'Показать технические подробности?', 'technical_title': 'Технические подробности', 'cancelled': 'Обработка отменена', 'cancelled_log': 'Обработка отменена пользователем.', 'cancel_request': 'Отмена операции...', 'cancel_requested_log': 'Запрошена отмена операции...', 'warning': 'Предупреждение', 'time_format': 'Введи время в формате ЧЧ:ММ:СС.', 'invalid_time_value': 'Некорректное время: {value}. Используй ЧЧ:ММ:СС или ММ:СС.', 'invalid_time_short': 'Некорректное время: {value}.', 'negative_time': 'Время не может быть отрицательным.', 'minutes_seconds': 'Минуты и секунды должны быть меньше 60.', 'seconds_less': 'Секунды должны быть меньше 60.', 'overwrite_warning': 'Предупреждение: {message}', 'yt_error': 'Ошибка yt-dlp: {message}'}, 'en': {'menu_help': 'Help', 'menu_about': 'About Extract Audio', 'menu_exit': 'Quit', 'help_missing': 'Help file not found. Place HELP_en.md next to the app or include it in the build.', 'close': 'Close', 'about_title': 'About Extract Audio', 'version': 'Version', 'architecture_arm': 'For Apple Silicon Mac (arm64)', 'architecture_intel': 'For Intel Mac (x86_64)', 'description': 'A tool for extracting audio from video\nand preparing recordings for transcription.', 'author': 'Author', 'subtitle': 'Extract audio from video for transcription', 'source_video': 'Video source', 'local_file': 'File on this computer', 'choose_video': 'Choose video', 'youtube_vimeo': 'YouTube or Vimeo link', 'url_note': 'Available videos can be downloaded. Videos with access restrictions may not be available.', 'segment': 'Audio segment (optional)', 'segment_note': 'Leave both fields empty to extract all audio. Time format: HH:MM:SS, for example 00:35:00.', 'start': 'Start:', 'end': 'End:', 'quality': 'MP3 quality', 'bitrate': 'Bitrate:', 'kbps_note': 'kbps — 48–64 is usually enough for speech', 'extract': 'Extract audio', 'cancel': 'Cancel', 'log': 'Processing log', 'video_none': 'No video selected', 'ready': 'Ready', 'choose_video_title': 'Choose a video', 'video_files': 'Video files', 'all_files': 'All files', 'video_selected': 'Video selected', 'selected_video': 'Selected video:', 'no_video_title': 'No video', 'choose_first': 'Choose a video file first.', 'error': 'Error', 'source_missing': 'The source video file was not found.', 'no_url_title': 'No link', 'paste_url': 'Paste a video link.', 'unsupported_url': 'Unsupported link', 'paste_supported_url': 'Enter a YouTube or Vimeo link.', 'interval_missing': 'Missing time range', 'interval_both': 'Enter both the start and end times, or leave both fields empty.', 'invalid_time': 'Invalid time', 'invalid_interval': 'Invalid time range', 'end_after_start': 'The end time must be later than the start time.', 'file_exists': 'File already exists', 'overwrite': 'This file already exists:\n\n{path}\n\nOverwrite it?', 'prepare': 'Preparing video...', 'preparing': 'Preparing...', 'source_local': 'Source: local file', 'source_url': 'Source: {url}', 'audio_quality': 'Audio quality: {quality} kbps', 'fragment': 'Segment: {start} — {end}', 'all_audio': 'Mode: full audio', 'downloading_stream': 'Downloading audio stream...', 'connecting': 'Connecting to source...', 'download_percent': 'Downloading audio: {percent:.1f}%', 'stream_downloaded': 'Audio stream downloaded. Starting processing...', 'yt_no_file': 'yt-dlp did not create an audio stream file.', 'download_failed': 'Could not download video: {error}', 'ffmpeg_missing_frozen': 'Could not start the audio processing component. Reinstall the app.', 'ffmpeg_missing_dev': 'FFmpeg not found. Check the development installation.', 'extracting': 'Extracting audio...', 'save_file': 'Saving file...', 'saving_audio': 'Saving audio file...', 'done': 'Done!', 'saved': 'Done! Audio saved.', 'success': 'Audio was saved successfully:\n\n{path}', 'processing_failed': 'Could not process video', 'processing_failed_log': 'Could not process video.', 'processing_error': 'Processing error', 'technical_details': 'Show technical details?', 'technical_title': 'Technical details', 'cancelled': 'Operation cancelled', 'cancelled_log': 'Operation cancelled by user.', 'cancel_request': 'Cancelling operation...', 'cancel_requested_log': 'Cancellation requested...', 'warning': 'Warning', 'time_format': 'Enter time in HH:MM:SS format.', 'invalid_time_value': 'Invalid time: {value}. Use HH:MM:SS or MM:SS.', 'invalid_time_short': 'Invalid time: {value}.', 'negative_time': 'Time cannot be negative.', 'minutes_seconds': 'Minutes and seconds must be less than 60.', 'seconds_less': 'Seconds must be less than 60.', 'overwrite_warning': 'Warning: {message}', 'yt_error': 'yt-dlp error: {message}'}}

def tr(key, **kwargs):
    text = TRANSLATIONS.get(LANGUAGE, TRANSLATIONS["en"]).get(
        key, TRANSLATIONS["en"].get(key, key)
    )
    return text.format(**kwargs) if kwargs else text

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
        raise ValueError(tr("time_format"))

    parts = value.split(":")
    if len(parts) not in (2, 3):
        raise ValueError(
            tr("invalid_time_value", value=value)
        )

    try:
        numbers = [float(part) for part in parts]
    except ValueError as error:
        raise ValueError(tr("invalid_time_short", value=value)) from error

    if any(number < 0 for number in numbers):
        raise ValueError(tr("negative_time"))

    if len(numbers) == 3:
        hours, minutes, seconds = numbers
        if minutes >= 60 or seconds >= 60:
            raise ValueError(tr("minutes_seconds"))
        return hours * 3600 + minutes * 60 + seconds

    minutes, seconds = numbers
    if seconds >= 60:
        raise ValueError(tr("seconds_less"))
    return minutes * 60 + seconds


def format_time(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class ExtractAudioApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
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
        self.file_label = tk.StringVar(value=tr("video_none"))
        self.status = tk.StringVar(value=tr("ready"))
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
        app_menu.add_command(label=tr("menu_help"), command=self._show_help)
        app_menu.add_command(label=tr("menu_about"), command=self._show_about)
        app_menu.add_separator()
        app_menu.add_command(label=tr("menu_exit"), command=self._on_close)
        menu_bar.add_cascade(label=tr("menu_about") if LANGUAGE == "en" else ("File" if LANGUAGE == "en" else "Файл" if LANGUAGE == "ru" else "Файл"), menu=app_menu)
        self.root.configure(menu=menu_bar)

    def _help_file_path(self):
        if getattr(sys, "frozen", False):
            return Path(sys._MEIPASS) / HELP_FILES[LANGUAGE]
        return Path(__file__).resolve().with_name(HELP_FILES[LANGUAGE])

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
        window.title(f"{tr('menu_help')} — {APP_NAME}")
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
            text=tr("close"),
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
        window.title(tr("about_title"))
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
            text=f"{tr('version')} {APP_VERSION} · {BUILD_NUMBER}",
        ).pack(pady=(0, 8))

        # This release is built for Intel Macs only (x86_64).
        ttk.Label(
            content,
            text=tr("architecture_intel"),
            foreground="#1769aa",
            font=("Helvetica", 10, "bold"),
        ).pack(pady=(0, 14))

        ttk.Label(
            content,
            text=tr("description"),
            justify="center",
            wraplength=360,
        ).pack(pady=(0, 14))

        ttk.Label(content, text=f"{tr('author')}: {APP_AUTHOR}").pack(pady=(0, 4))

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
        ttk.Button(content, text=tr("close"), command=window.destroy).pack()

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
            text=tr("subtitle"),
        ).pack(anchor="w", pady=(2, 4))

        # Compatibility notice: this build targets Intel Macs only.
        ttk.Label(
            main,
            text=tr("architecture_intel"),
            foreground="#1769aa",
            font=("Helvetica", 10, "bold"),
        ).pack(anchor="w", pady=(0, 14))

        file_frame = ttk.LabelFrame(main, text=tr("source_video"), padding=10)
        file_frame.pack(fill="x", pady=(0, 10))

        ttk.Radiobutton(
            file_frame, text=tr("local_file"), variable=self.source_mode,
            value="file", command=self._update_source_mode,
        ).pack(anchor="w")
        file_row = ttk.Frame(file_frame)
        file_row.pack(fill="x", pady=(4, 8))
        self.file_label_widget = ttk.Label(
            file_row, textvariable=self.file_label, wraplength=470
        )
        self.file_label_widget.pack(side="left", fill="x", expand=True)
        self.choose_button = ttk.Button(
            file_row, text=tr("choose_video"), command=self._choose_video
        )
        self.choose_button.pack(side="right", padx=(8, 0))
        ttk.Separator(file_frame).pack(fill="x", pady=5)
        ttk.Radiobutton(
            file_frame, text=tr("youtube_vimeo"),
            variable=self.source_mode, value="url",
            command=self._update_source_mode,
        ).pack(anchor="w")
        self.url_entry = ttk.Entry(file_frame, textvariable=self.source_url)
        self.url_entry.pack(fill="x", pady=(5, 2))
        ttk.Label(
            file_frame,
            text=tr("url_note"),
            foreground="gray", wraplength=690,
        ).pack(anchor="w")

        segment_frame = ttk.LabelFrame(
            main,
            text=tr("segment"),
            padding=10,
        )
        segment_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(
            segment_frame,
            text=(
                tr("segment_note") + " " if False else "Оставь оба поля пустыми, чтобы извлечь всё аудио. "
                "Формат времени: ЧЧ:ММ:СС, например 00:35:00."
            ),
            foreground="gray",
            wraplength=690,
        ).pack(anchor="w", pady=(0, 8))

        time_row = ttk.Frame(segment_frame)
        time_row.pack(fill="x")

        ttk.Label(time_row, text=tr("start")).pack(side="left")
        self.start_entry = ttk.Entry(
            time_row,
            textvariable=self.start_time,
            width=13,
        )
        self.start_entry.pack(side="left", padx=(6, 16))

        ttk.Label(time_row, text=tr("end")).pack(side="left")
        self.end_entry = ttk.Entry(
            time_row,
            textvariable=self.end_time,
            width=13,
        )
        self.end_entry.pack(side="left", padx=6)

        quality_frame = ttk.LabelFrame(main, text=tr("quality"), padding=10)
        quality_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(quality_frame, text=tr("bitrate")).pack(side="left")

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
            text=tr("kbps_note"),
        ).pack(side="left")

        controls = ttk.Frame(main)
        controls.pack(fill="x", pady=(0, 10))

        self.start_button = ttk.Button(
            controls,
            text=tr("extract"),
            command=self._start,
        )
        self.start_button.pack(side="left")

        self.cancel_button = ttk.Button(
            controls,
            text=tr("cancel"),
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
            text=tr("log"),
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
            title=tr("choose_video_title"),
            filetypes=[
                (tr("video_files"), VIDEO_FORMATS),
                (tr("all_files"), "*.*"),
            ],
        )

        if filename:
            self.video_path = Path(filename)
            self.file_label.set(self.video_path.name)
            self.status.set(tr("video_selected"))
            self._write_log(f"{tr('selected_video')} {self.video_path}")

    def _ffmpeg_path(self):
        if getattr(sys, "frozen", False):
            bundled_path = Path(sys._MEIPASS) / "ffmpeg"
            if bundled_path.is_file():
                return str(bundled_path)
            raise FileNotFoundError(
                tr("ffmpeg_missing_frozen") + " "
                "Переустановите приложение."
            )

        path = shutil.which("ffmpeg")
        if path:
            return path

        local_path = Path.home() / "bin" / "ffmpeg"
        if local_path.is_file():
            return str(local_path)

        raise FileNotFoundError(
            tr("ffmpeg_missing_dev")
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
                messagebox.showwarning(tr("no_video_title"), tr("choose_first"), parent=self.root)
                return
            if not self.video_path.is_file():
                messagebox.showerror(tr("error"), tr("source_missing"), parent=self.root)
                return
            source_path = self.video_path
        else:
            if not url:
                messagebox.showwarning(tr("no_url_title"), tr("paste_url"), parent=self.root)
                return
            if not is_supported_url(url):
                messagebox.showwarning(tr("unsupported_url"), tr("paste_supported_url"), parent=self.root)
                return

        start_text = self.start_time.get().strip()
        end_text = self.end_time.get().strip()
        if bool(start_text) != bool(end_text):
            messagebox.showwarning(tr("interval_missing"), tr("interval_both"), parent=self.root)
            return
        start_seconds = end_seconds = None
        if start_text and end_text:
            try:
                start_seconds = parse_time(start_text)
                end_seconds = parse_time(end_text)
            except ValueError as error:
                messagebox.showwarning(tr("invalid_time"), str(error), parent=self.root)
                return
            if end_seconds <= start_seconds:
                messagebox.showwarning(tr("invalid_interval"), tr("end_after_start"), parent=self.root)
                return

        output_path = self._make_output_path(start_seconds, end_seconds) if mode == "file" else None
        if output_path and output_path.exists():
            if not messagebox.askyesno(tr("file_exists"), tr("overwrite", path=output_path), parent=self.root):
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

        self.status.set(tr("prepare"))
        self._write_log("-" * 45)
        self._write_log(tr("preparing"))
        self._write_log(tr("source_local") if mode == "file" else tr("source_url", url=url))
        self._write_log(tr("audio_quality", quality=self.output_quality))

        if start_seconds is not None:
            self._write_log(
                f"Фрагмент: {format_time(start_seconds)} — "
                f"{format_time(end_seconds)}"
            )
        else:
            self._write_log(tr("all_audio"))

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
            self.events.put(("status", tr("downloading_stream")))
            self.events.put(("log", tr("connecting")))
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
                            self.events.put(("status", tr("download_percent", percent=current / total * 100)))
                    elif data.get("status") == "finished":
                        self.events.put(("log", tr("stream_downloaded")))

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
                        raise FileNotFoundError(tr("yt_no_file"))
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
                self.events.put(("error", tr("download_failed", error=error)))
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

            self.events.put(("status", tr("extracting")))

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
                    if value == tr("extracting"):
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
                    self.status.set(tr("save_file"))
                    self._write_log(tr("saving_audio"))

                elif event == "diagnostic":
                    self.diagnostic_text = value

                elif event == "output_exists":
                    overwrite = messagebox.askyesno(
                        tr("file_exists"),
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
                    self.status.set(tr("done"))
                    self._write_log(tr("saved"))

                    messagebox.showinfo(
                        "Готово",
                        tr("success", path=value),
                        parent=self.root,
                    )

                elif event == "error":
                    self._finish()
                    self.status.set(tr("processing_failed"))
                    self._write_log(tr("processing_failed_log"))

                    details = getattr(self, "diagnostic_text", "")
                    if details:
                        show_details = messagebox.askyesno(
                            tr("processing_error"),
                            f"{value}\n\n{tr('technical_details')}",
                            parent=self.root,
                        )
                        if show_details:
                            messagebox.showerror(
                                tr("technical_title"),
                                details[:5000],
                                parent=self.root,
                            )
                    else:
                        messagebox.showerror(
                            tr("error"),
                            value,
                            parent=self.root,
                        )

                elif event == "cancelled":
                    self._finish()
                    self.status.set(tr("cancelled"))
                    self._write_log(tr("cancelled_log"))

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
        self.status.set(tr("cancel_request"))
        self._write_log(tr("cancel_requested_log"))

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
        self.events.put(("log", tr("overwrite_warning", message=message)))

    def error(self, message):
        self.events.put(("log", tr("yt_error", message=message)))


def main():
    root = tk.Tk()
    ExtractAudioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
