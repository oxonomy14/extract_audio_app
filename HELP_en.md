# Extract Audio — Help

**Version:** 0.2.0-beta.1  
**Build:** Build 1  
**Author:** Andrii Semenenko
**Last code update:** October 21, 2026

Extract Audio extracts audio from local video files or accessible YouTube/Vimeo links and saves the result as MP3.

## Extract audio from a file
1. Select “File on this computer”.
2. Click “Choose video” and select the source file.
3. Choose the MP3 bitrate.
4. Optionally enter the start and end of a segment.
5. Click “Extract audio”.

For local files, the result is saved next to the source video. For a segment, the selected time range is added to the output filename.

## Extract audio from a link
1. Select “YouTube or Vimeo link”.
2. Paste a link to an accessible video.
3. Choose the bitrate and an optional time range.
4. Click “Extract audio”.

The MP3 is saved to Downloads if that folder is available; otherwise, it is saved in your home folder. A video may be unavailable because of privacy settings, authentication requirements, platform restrictions, or website changes. Only download material you are authorized to access.

## Time range
Leave both fields empty to process the entire recording. To extract a segment, enter both the start and end times. Supported formats are `HH:MM:SS` and `MM:SS`. For example, `00:35:00` to `01:20:00` is 45 minutes. The end time must be later than the start time and must not exceed the recording duration.

## MP3 bitrate
Available bitrates are 32, 48, 64, 96, 128, and 192 kbps. Lower bitrates create smaller files and are often suitable for speech. 96–192 kbps usually preserve more detail but increase file size. A higher bitrate cannot restore quality that is absent from the source.

## Progress and cancellation
The app displays status, progress, and a processing log. Click “Cancel” to request that the operation stop. Cancellation may take some time during network downloads.

## Troubleshooting
- **FFmpeg not found:** in development mode, check `PATH` or the `~/bin/ffmpeg` location.
- **SSL error:** check the macOS date and time, your connection, and the installed `certifi` package.
- **Video unavailable:** open the link in a browser and check access requirements.
- **Time range error:** check the format and recording duration.
- **Not enough disk space:** check available disk space.

## Technical components
The app uses Python, Tkinter, FFmpeg, yt-dlp, and certifi. Link downloads require an internet connection and depend on yt-dlp support for the relevant website.

## Responsibility
Users are responsible for complying with copyright, platform terms, and applicable law.

## Developer contact
**Developer:** Andrii Semenenko

**Website:** https://andriiweb.dev

**Email:** hello@andriiweb.dev
