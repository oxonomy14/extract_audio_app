# Extract Audio

**Version:** 0.2.0-beta.1 · **Build:** 1\
**Author:** Andrii Semenenko

Extract Audio is a desktop application built with Python/Tkinter for
extracting audio from local video files and accessible YouTube/Vimeo
links.

## Features

-   Extract audio from local video files.
-   Download available audio streams from YouTube/Vimeo links.
-   Export MP3 at 32, 48, 64, 96, 128, or 192 kbps.
-   Select a time range to extract.
-   Progress indicator, log, error reporting, and cancellation.
-   Built-in Help and About windows.

## macOS architecture files

Separate source and PyInstaller spec files are used for each macOS
architecture:

  -----------------------------------------------------------------------------------
  Architecture            Python entry point       PyInstaller spec
  ----------------------- ------------------------ ----------------------------------
  Intel (`x86_64`)        `main_macos_x86_64_localized.py`   `ExtractAudio_macos_x86_64_localized.spec`

  Apple Silicon (`arm64`, `main_macos_arm64_localized.py`    `ExtractAudio_macos_arm64_localized.spec`
  e.g. M1/M2/M3/M4)                                
  -----------------------------------------------------------------------------------

Build on a Mac using native Python for the target architecture. Check
the architecture of your Python installation with:

``` bash
python3 -c "import platform; print(platform.machine())"
```

Expected output: `x86_64` for Intel or `arm64` for Apple Silicon.

## Run from source

Install Python dependencies:

``` bash
python3 -m pip install -U yt-dlp certifi
```

Make sure FFmpeg is available on `PATH` or at `~/bin/ffmpeg`. Keep
`HELP.md` in the project root beside the source files. For example, to
run the Apple Silicon version:

``` bash
python3 main_macos_arm64_localized.py
```

## Build for macOS

Install PyInstaller and the Python dependencies:

``` bash
python3 -m pip install -U pyinstaller yt-dlp certifi
```

### Apple Silicon (`arm64`)

Run from the project root on an Apple Silicon Mac:

``` bash
python3 -m PyInstaller --clean ExtractAudio_macos_arm64_localized.spec
```

Expected app path:

``` text
dist/Extract Audio.app
```

### Intel (`x86_64`)

Run from the project root on an Intel Mac:

``` bash
python3 -m PyInstaller --clean ExtractAudio_macos_x86_64_localized.spec
```

The output location and app name depend on the settings in the
corresponding spec file.

Before building, check the spec file for: - the correct Python
entry-point path; - the FFmpeg path; - the presence of
`ExtractAudio.icns` and `HELP_localized.md`; - inclusion of FFmpeg and `certifi`
in the bundle.

After building, launch the app and test MP3 extraction. A successful
build alone does not guarantee compatibility with every macOS version or
another Mac.

## Create a DMG with an Applications shortcut

The commands below are for Apple Silicon and assume the app was built at
`dist/Extract Audio.app`. Run them from the project root.

Prepare the DMG contents:

``` bash
mkdir -p release/dmg
rm -rf "release/dmg/Extract Audio.app"
cp -R "dist/Extract Audio.app" "release/dmg/"
ln -s /Applications "release/dmg/Applications"
```

Create the DMG:

``` bash
hdiutil create \
  -volname "Extract Audio" \
  -srcfolder "release/dmg" \
  -ov \
  -format UDZO \
  "release/ExtractAudio_0.2.0-beta.1_macOS_AppleSilicon.dmg"
```

Verify the image:

``` bash
hdiutil verify "release/ExtractAudio_0.2.0-beta.1_macOS_AppleSilicon.dmg"
```

When the user opens the DMG in Finder, they can drag `Extract Audio.app`
onto the `Applications` shortcut.

For Intel builds, use the app produced by the Intel spec and give the
DMG a name that clearly identifies it as Intel or `x86_64`.

## Signing and macOS warnings

This free build may be unsigned and not notarized by Apple. On another
Mac, macOS may display a warning about an unidentified developer. Keep
this in mind when sharing the app with other users.

## Important notes

-   The app requires FFmpeg. Before public distribution, verify that all
    required libraries are bundled and load correctly on a Mac without
    Homebrew installed.
-   Link downloads depend on video availability and the current support
    provided by `yt-dlp`.
-   Only download material you are authorized to access.

------------------------------------------------------------------------

# Extract Audio

**Версія:** 0.2.0-beta.1 · **Build:** 1\
**Автор:** Andrii Semenenko

Extract Audio --- настільний застосунок на Python/Tkinter для вилучення
аудіо з локальних відеофайлів і доступних посилань YouTube/Vimeo.

## Можливості

-   Вилучення аудіо з локальних відеофайлів.
-   Завантаження доступних аудіопотоків за посиланнями YouTube/Vimeo.
-   Збереження у MP3 з бітрейтом 32, 48, 64, 96, 128 або 192 кбіт/с.
-   Вибір часового фрагмента.
-   Індикатор прогресу, журнал, повідомлення про помилки та скасування
    операції.
-   Вбудовані вікна «Довідка» та «Про програму».

## Файли для архітектур macOS

Для кожної архітектури macOS використовуються окремі файли запуску та
конфігурації PyInstaller:

  -----------------------------------------------------------------------------------
  Архітектура             Основний Python-файл     Файл конфігурації PyInstaller
  ----------------------- ------------------------ ----------------------------------
  Intel (`x86_64`)        `main_macos_x86_64_localized.py`   `ExtractAudio_macos_x86_64_localized.spec`

  Apple Silicon (`arm64`, `main_macos_arm64_localized.py`    `ExtractAudio_macos_arm64_localized.spec`
  наприклад M1/M2/M3/M4)                           
  -----------------------------------------------------------------------------------

Збирайте застосунок на Mac із нативною версією Python для відповідної
архітектури. Перевірити архітектуру Python можна командою:

``` bash
python3 -c "import platform; print(platform.machine())"
```

Очікуваний результат: `x86_64` для Intel або `arm64` для Apple Silicon.

## Запуск із вихідного коду

Установіть залежності Python:

``` bash
python3 -m pip install -U yt-dlp certifi
```

Переконайтеся, що FFmpeg доступний через `PATH` або розташований за
шляхом `~/bin/ffmpeg`. Файл `HELP.md` має бути в кореневій папці проєкту
поруч із файлами вихідного коду. Наприклад, для Apple Silicon:

``` bash
python3 main_macos_arm64.py
```

## Збирання для macOS

Установіть PyInstaller і залежності Python:

``` bash
python3 -m pip install -U pyinstaller yt-dlp certifi
```

### Apple Silicon (`arm64`)

На Mac з Apple Silicon виконайте команду з кореневої папки проєкту:

``` bash
python3 -m PyInstaller --clean ExtractAudio_macos_arm64_localized.spec
```

Очікуваний шлях до застосунку:

``` text
dist/Extract Audio.app
```

### Intel (`x86_64`)

На Intel Mac виконайте з кореневої папки проєкту:

``` bash
python3 -m PyInstaller --clean ExtractAudio_macos_x86_64_localized.spec
```

Місце розташування та назва готового застосунку залежать від параметрів
у відповідному файлі `.spec`.

Перед збиранням перевірте у файлі `.spec`: - правильний шлях до
основного Python-файлу; - шлях до FFmpeg; - наявність
`ExtractAudio.icns` і `HELP_localized.md`; - включення FFmpeg і `certifi` до
пакета.

Після збирання запустіть застосунок і перевірте вилучення MP3. Успішне
збирання саме по собі не гарантує сумісності з усіма версіями macOS або
іншими комп'ютерами.

## Створення DMG із ярликом «Програми»

Наведені нижче команди призначені для Apple Silicon і передбачають, що
застосунок зібрано в `dist/Extract Audio.app`. Виконуйте їх із кореневої
папки проєкту.

Підготуйте вміст DMG:

``` bash
mkdir -p release/dmg
rm -rf "release/dmg/Extract Audio.app"
cp -R "dist/Extract Audio.app" "release/dmg/"
ln -s /Applications "release/dmg/Applications"
```

Створіть DMG:

``` bash
hdiutil create \
  -volname "Extract Audio" \
  -srcfolder "release/dmg" \
  -ov \
  -format UDZO \
  "release/ExtractAudio_0.2.0-beta.1_macOS_AppleSilicon.dmg"
```

Перевірте образ:

``` bash
hdiutil verify "release/ExtractAudio_0.2.0-beta.1_macOS_AppleSilicon.dmg"
```

Після відкриття DMG у Finder користувач зможе перетягнути
`Extract Audio.app` на ярлик `Applications`.

Для Intel-збирання використовуйте застосунок, створений відповідним
Intel-файлом `.spec`, і вкажіть у назві DMG архітектуру `Intel` або
`x86_64`.

## Підпис і попередження macOS

Ця безкоштовна збірка може бути непідписаною та не нотаризованою Apple.
На іншому Mac macOS може показати попередження про невідомого
розробника. Враховуйте це, передаючи застосунок іншим користувачам.

## Важливі примітки

-   Для роботи застосунку потрібен FFmpeg. Перед публічним
    розповсюдженням перевірте, що всі необхідні бібліотеки включені до
    пакета й завантажуються на Mac без установленого Homebrew.
-   Завантаження за посиланнями залежить від доступності відео та
    поточної підтримки сайту в `yt-dlp`.
-   Завантажуйте лише матеріали, до яких маєте законний доступ.
