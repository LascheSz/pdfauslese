import PyPDF2
import os
import re
import shutil
import time

from googletrans import Translator
from langdetect import DetectorFactory
from loguru import logger

# Globale Variablen
DATEIENDUNG = ".pdf"
ORDNER = "C:/Users/em/Desktop/Test/"
WARTEZEIT = 10
FINISHED = os.path.join(ORDNER, "finished")
LANGUAGE_CODE = "de"
log = logger
LOG_DATEI = "C:/code/python/PDFAuslesen/output.log"

'''
replacements = {
        "°C": " Grad Celsius",
        "°": " Grad",
        "&": " und ",
        "%": " Prozent\n",
        "€": " Euro",
        "tevigo GmbH  · Raiffeisenstr. 2 D · 38159 Vechelde (Germany) · www.gardigo.de": "",
        "Service-Hotline Telefon (0 53 02) 9 34 87 88": "",
        "Ihr Gardigo-Team": "",
        "• ": "",
        "•": "",
        "•  ": "",
        ":": "",
        ")": "",
        "(": "",
        "{": "",
        "}": "",
        "[": "",
        "]": "",
        "1. ": "1 ",
        "2. ": "2 ",
        "3. ": "3 ",
        "4. ": "4 ",
        "5. ": "5 ",
        "1.)": "1 ",
        "2.)": "2 ",
        "3.)": "3 ",
        "4.)": "4 ",
        "5.)": "5 ",
    }
'''

# Logger konfigurieren
logger.add(
    LOG_DATEI,
    rotation="10 MB",
    retention="10 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {file} | {line} | {level} | {message}"
)

DetectorFactory.seed = 0


# Funktion zur Prüfung und Erstellung der benötigten Ordner
'''
def check_ordner():
    if not os.path.exists(ORDNER):
        log.warning(f"{ORDNER} existiert nicht!")
        os.mkdir(ORDNER)
        log.success(f"{ORDNER} wurde erstellt")
    if not os.path.exists(FINISHED):
        log.warning(f"{FINISHED} existiert nicht!")
        os.mkdir(FINISHED)
        log.success(f"{FINISHED} wurde erstellt")
    if os.path.exists(ORDNER) and os.path.exists(FINISHED):
        log.info("Alle benötigten Ordner existieren!")
        check_files()
'''


# Funktion zum Durchsuchen und Verarbeiten der Dateien im Ordner
def check_files():
    files_list = os.listdir(ORDNER)
    if "finished" in files_list:
        files_list.remove("finished")
    if len(files_list) == 0:
        log.info("Es sind keine Dateien vorhanden")
        return check_files()
    log.info(f"Es sind insgesamt {len(files_list)} Dateien enthalten: {files_list}")
    for filename in files_list:
        if filename.endswith(DATEIENDUNG):
            logger.info(f"PDF-Datei gefunden: {filename}")
            text = ""
            try:
                file_pfad = os.path.join(ORDNER, filename)
                with open(file_pfad, "rb") as file:
                    reader = PyPDF2.PdfReader(file)
                    for page in reader.pages:
                        text += page.extract_text() + " \n"
                    logger.debug(text)
                retry_move(file_pfad, os.path.join(FINISHED, filename))
                logger.info(f"Folgende PDF-Datei wurde verschoben: {filename}")
                detect_language(text, filename)
            except Exception as error:
                logger.error(f"Fehler beim Verarbeiten der Datei {filename}: {error}")


def retry_move(src, dst, retries=3, delay=5):
    for i in range(retries):
        try:
            shutil.move(src, dst)
            return
        except Exception as error:
            logger.error(f"Fehler beim Verschieben der Datei: {error}")
            time.sleep(delay)
    logger.error(f"Fehler beim Verschieben der Datei nach {retries} Versuchen")


# Funktion zur Spracherkennung und Filterung
def detect_language(text, filename):
    log.debug(f"Der übergebene Text von {filename} wird nun in {LANGUAGE_CODE} gefiltert")
    text = replace_special(text)
    translator = Translator()
    filtered_text = ""
    for line in text.split("\n"):
        if not line.strip():
            continue
        try:
            result = translator.detect(line)
            '''result = better_result(real_result)'''
            if result and result.lang == LANGUAGE_CODE:
                filtered_text += line + "\n"
                '''confidence = result.confidence if hasattr(result, "confidence") else "None"'''
            log.debug(f"Confidence {result.confidence} | Erkannte Sprache: {result.lang} für Text: {line}")
        except Exception as error:
            log.error(f"Fehler beim Erkennen der Sprache für Zeile: {line.strip()} | Fehler: {error}")


replacements = {"°C": " Grad Celsius",
                "°": " Grad ",
                "&": "und ",
                "%": "Prozent\n",
                "€": " Euro ",
                "tevigo GmbH  · Raiffeisenstr.": "",
                "tevigo GmbH  · Raiffeisenstr. 2 D · 38159 Vechelde (Germany) · www.gardigo.de": "",
                "Service-Hotline Telefon (0 53 02) 9 34 87 88": "",
                "Ihr Gardigo-Team": "",
                "Service-Hotline: Telefon (0 53 02) 9 34 87 88": "",
                "com": "",
                "de": "",
                "gardigo.": "",
                "2 D · 38159 Vechelde Germany · www.": "",
                "Service Hotline": "",
                "Phone +49 0 53 02 9 34 87 88": "",
                "Your Gardigo-Team": "",
                "• ": "",
                "•": "",
                "•  ": "",
                ":": "",
                ")": "",
                "(": "",
                "{": "",
                "}": "",
                "[": "",
                "]": "",
                "1. ": "1 ",
                "2. ": "2 ",
                "3. ": "3 ",
                "4. ": "4 ",
                "5. ": "5 ",
                "1.)": "1 ",
                "2.)": "2 ",
                "3.)": "3 ",
                "4.)": "4 ",
                "5.)": "5 ",
                }


def replace_special(text):
    lines = text.split("\n")
    merged_lines = []
    pattern = r"(?<=\d)\,(?=\d)"
    pattern1 = r"(?<=\d)\.(?=\d)"
    for line in lines:
        if re.search(pattern1, line) or re.search(pattern, line):
            for old, new in replacements.items():
                line = line.replace(old, new)  # Ersetzungen vornehmen
            merged_lines.append(line.strip())
        else:
            line = re.sub(r",", "", line)  # Entferne ',' wenn keine Zahlen davor oder danach sind
            line = re.sub(r"\.", ".\n", line)  # Ersetze '.' mit '.\n' wenn keine Zahlen davor oder danach sind
            for old, new in replacements.items():
                line = line.replace(old, new)  # Ersetzungen vornehmen
            merged_lines.append(line.strip())
    return "\n".join(merged_lines)  # Alle Zeilen wieder zusammenfügen


def better_result(result):
    result = result
    if result.lang != result.previous_line.lang and result.lang != result.next_line.lang:
        previous_line = result.previous_line
        next_line = result.next_line
        if previous_line and next_line and previous_line.lang == next_line.lang:
            result.lang = previous_line.lang
    return result


'''
def replace_lines(text):
    lines = text.split("\n")
    buffer_line = ""
    final_lines = []
    skip_next = False

    # Zusammenführen von Zeilen
    for i, line in enumerate(lines):
        if line.endswith("-") and i + 1 < len(lines):
            next_line = lines[i + 1]
            if next_line and next_line[0].islower():
                buffer_line += line[:-1] + next_line
                skip_next = True
                continue
            else:
                buffer_line += line[:-1]
        else:
            if skip_next:
                skip_next = False
                continue
            buffer_line += line

    # Punkt markiert das Zeilenende
    if "." in buffer_line or "%" in buffer_line:
        parts = re.split(r'[.%]', buffer_line)
        for part in parts[:-1]:
            if "etc." in part:
                buffer_line += part.strip() + "."
            else:
                final_lines.append(part.strip() + ".")
                final_lines.append("")
        buffer_line = parts[-1]

    if buffer_line.strip():
        final_lines.append(buffer_line.strip())

    # Ersetzte Textzeilen
    replaced_text = "\n".join(final_lines)
    lines = replaced_text.split("\n")
    merged_lines = []

    for line in lines:
        matches = re.findall(pattern, line)
        if matches:
            for old, new in replacements.items():
                line = line.replace(old, new)
        else:
            replacements.update({",": ""})
            for old, new in replacements.items():
                line = line.replace(old, new)
        merged_lines.append(line.strip())

    return "\n".join(merged_lines)
'''

'''
def safe_text_in_file(filtered_text, filename):
    pass
'''

# Hauptprogramm
if __name__ == "__main__":
    try:
        while True:
            '''check_ordner()'''
            time.sleep(WARTEZEIT)
    except KeyboardInterrupt:
        log.success("Das Programm wurde erfolgreich beendet. Grund: KeyboardInterrupt")
