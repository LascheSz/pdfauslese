import PyPDF2
import os
import re
from loguru import logger
import time
import langid
from dotenv import load_dotenv


load_dotenv()

DATEIENDUNG = ".pdf"
ORDNER = "C:/Users/em/Desktop/Test/"
WARTEZEIT = 10
FINISHED = os.path.join(ORDNER, "finished")
LANGUAGE_CODE = "de"
log = logger
LOG_DATEI = "C:/code/python/PDFAuslesen/output.log"
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")


# Konfiguration des Loggers
logger.add(
    LOG_DATEI,
    rotation="10 MB",
    retention="10 days",
    compression="zip",
    format="{time:DD.MM.YYYY HH:mm:ss} | {file} | {line} | {level} | {message}"
)


# Funktion zur Prüfung und Erstellung der benötigten Ordner
def check_ordner():
    """
    Prüft das Vorhandensein der benötigten Ordner und erstellt sie bei Bedarf.

    Args:
        'None'

    Returns:
        None
    """
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
        check_pdf()


def check_pdf():
    """
    Überprüft das Vorhandensein von PDF-Dateien im Ordner und verarbeitet sie.

    Args:
        'None'

    Returns:
        None
    """
    files_list = os.listdir(ORDNER)
    if "finished" in files_list:
        files_list.remove("finished")
    if "output.log" in files_list:
        files_list.remove("output.log")
    for file_endswith in files_list:
        if file_endswith.endswith(".pdf"):
            if len(files_list) == 0:
                log.info("Es sind keine Dateien vorhanden")
                return check_pdf()
            log.info(f"Es sind insgesamt {len(files_list)} Dateien enthalten: {files_list}")
            for filename in files_list:
                if filename.endswith(".pdf"):
                    logger.info(f"PDF-Datei gefunden: {filename}")
                    text = ""
                    try:
                        file_pfad = os.path.join(ORDNER, filename)
                        with open(file_pfad, "rb") as file:
                            reader = PyPDF2.PdfReader(file)
                            for page in reader.pages:
                                text += "\n " + page.extract_text() + " \n"
                            logger.debug(text)
                            text = remove_hyphen(text, filename)
                            text, average_conf = lang_detect(text, filename)
                            log.debug(f"--------------------{filename}---------------------\n{text.strip()}\n--------------------{filename}---------------------\nDurchschnittliche Konfidenz: {average_conf}")
                        '''retry_move(file_pfad, os.path.join(FINISHED, filename))'''
                        logger.info(f"Folgende PDF-Datei wurde verschoben: {filename}")
                    except Exception as error:
                        logger.error(f"Fehler beim Verarbeiten der Datei {filename}: {error}")


def remove_hyphen(text, filename):
    """
    Removes hyphens at the end of lines caused by hyphenation.

    Args:
        text (str): The text from which hyphens should be removed.
        filename (str): The name of the file being processed.

    Returns:
        str: The text without hyphens at the end of lines.
    """
    log.info(f"Removing hyphens in the file {filename}")
    text = re.sub(r"-\n(?=[a-z])", "", text)
    return modify_line(text, filename)


def modify_line(text, filename):
    """
    Wendet verschiedene Regeln zur Zeilenumbruch- und Sonderzeichenentfernung an.

    Args:
        text (str): Der Text, der modifiziert werden soll.
        filename (str): Der Name der Datei, die verarbeitet wird.

    Returns:
        str: Der modifizierte Text.
    """
    log.info(f"Zeilenumbruch-Regeln werden angewendet in der Datei {filename}")

    # 1) Zeilenumbrüche entfernen, die nicht direkt von '.' oder '%' kommen
    text = re.sub(r'(?<![.%])\r?\n+', ' ', text)

    # 2) "echten" Punkt (kein Dezimalpunkt, kein etc.) → Umbruch
    #    - kein Umbruch nach "etc."
    #    - kein Umbruch bei Dezimalzahlen wie 3.14
    text = re.sub(r'(?<!etc)(?<!\d)\.(?!\d)', r'. \n', text)

    # 3) IMMER Umbruch nach '%'
    text = re.sub(r'%', '%\n', text)

    # 4) Alle Kommas entfernen, sofern sie nicht zwischen zwei Ziffern stehen
    # entfernt Kommas nur dann, wenn sie NICHT zwischen Ziffern stehen:
    text = re.sub(r'(?<!\d),(?!\d)', '', text)

    # 5) Leere Zeilen entfernen (z.B. wenn mehrere Umbrüche hintereinander entstehen)
    #    → '^' steht für Zeilenanfang, '\s*' beliebig Whitespace, '\n' der Zeilenumbruch
    #    → MULTILINE flag, damit '^' in jedem Zeilenkontext geprüft wird
    text = re.sub(r'^\s*\n', '', text, flags=re.MULTILINE)

    # (4) Alle Kommas entfernen, die NICHT zwischen zwei Ziffern stehen
    #     → So bleibt "1,5" bestehen, aber "Hallo, Welt" wird zu "Hallo Welt".
    text = re.sub(r'(?<!\d),(?!\d)', '', text)

    # Muster für Kommas zwischen zwei Ziffern (z. B. "1,5")
    # pattern = r"(?<=\d),(?=\d)"

    # Muster für Punkte zwischen zwei Ziffern → WEG, damit dezimale Punkte erhalten bleiben!
    # pattern1 = r"(?<=\d)\.(?=\d)"

    # Deine Ersetzungstabelle
    pattern2 = {
        "tevigo GmbH · Raiffeisenstr. 2 D · 38159 Vechelde (Germany) · www.gardigo.com": "",
        "Your Gardigo-Team": "",
        "Gardigo": "",
        " Ihr -Team ": "",
        "GmbH": "",
        "de   ": "",
        "Service Hotline: ": "",
        "Instruction Manual": "",
        "tevigo GmbH  · Raiffeisenstr. 2 D · 38159 Vechelde (Germany) · www.gardigo.de ": "",
        "tevigo   · Raiffeisenstr.": "",
        "2 D · 38159 Vechelde (Germany) · www.": "",
        "D-38159 Vechelde": "",
        "gardigo.": "",
        "com": "",
        "Service Hotline:": "",
        "Ihr Gardigo-Team": "",
        "Service-Hotline: Telefon (0 53 02) 9 34 87 88": "",
        "Phone +49 (0) 53 02 9 34 87 88": "",
        "lefon (0 53 02) 9 34 87 88Ihr -Teamtevigo   · Raiffeisenstr.": "",
        "de Art.": "Art. ",
        "-": " - ",
        "•  ": "",
        "•": "",
        "/": " ",
        ":": "\n",
        "(": "",
        ")": "",
        "%": "Prozent",
        "€": "Euro",
        "°": "Grad",
        "µ": "Mikro",
        "²": "Quadrat",
        "³": "Kubik",
        "½": "halb",
        "¼": "viertel",
        "¾": "dreiviertel",
        "°C": "Grad Celsius",
        "°F": "Grad Fahrenheit",
        "°Celsius": "Grad Celsius",
        "°Fahrenheit": "Grad Fahrenheit",
    }
    log.info(f"Entferne Sonderzeichen in der Datei {filename}")

    # Anschließend Strings austauschen nach dem Dictionary
    for old, new in pattern2.items():
        text = text.replace(old, new)

    # 6) Leere Zeilen entfernen (bzw. Leerzeichen am Zeilenanfang)
    #    → '^' steht für den Zeilenanfang
    #    -> '[ \t]+' bedeutet: ein oder mehr Leer- bzw. Tabzeichen
    #    → re.MULTILINE sorgt dafür, dass '^' in jedem Zeilenkontext geprüft wird
    text = re.sub(r'^[ \t]+', '', text, flags=re.MULTILINE)
    text = re.sub(r' {2,}', ' ', text)  # Remove double spaces

    return text


def dot_to_comma(text, filename):
    """
    Ersetzt alle Kommas durch Punkte im Text.

    Args:
        text (str): Der Text, in dem die Ersetzungen vorgenommen werden sollen.
        filename (str): Der Name der Datei, die verarbeitet wird.

    Returns:
        str: Der Text mit ersetzten Kommas.
    """
    log.info(f"Es wird nun jedes Komma durch einen Punkt ersetzt in der Datei {filename}")
    return re.sub(r",", ".", text)


def lang_detect(text, filename):
    """
    Erkennt die Sprache des Textes und filtert Zeilen, die in der gewünschten Sprache geschrieben sind.

    Args:
        text (str): Der zu analysierende Text.
        filename (str): Der Name der Datei, die verarbeitet wird.

    Returns:
        tuple: Ein Tupel bestehend aus dem gefilterten Text und der durchschnittlichen Konfidenz der Spracherkennung.
    """
    average_confi = 0
    log.info(f"Sprache wird herrausgesucht für die Datei {filename}")
    try:
        lines = text.split("\n")
        line_count = 0
        language_text = ""
        confidences = []
        for line in lines:
            if len(line) > 0:
                lang, confi = langid.classify(line)
                if lang == LANGUAGE_CODE:
                    language_text += line + "\n"
                    line_count += 1
                    confidences.append(confi)
                    print(confidences)
            average_confi = sum(confidences) / len(confidences)
        if line_count <= 5:
            log.warning(f"Die Datei {filename} enthält sehr wenig Zeilen in der Sprache {LANGUAGE_CODE}")
            log.warning(f"Es wurden nur {line_count} Zeilen gefunden")
            log.warning(f"Die Datei {filename} muss nun übersetzt werden")
            text = translate_text(text, filename)
            
            return text, average_confi
        else:
            return language_text.strip(), average_confi

    except Exception as error:
        log.error(f"Fehler beim Erkennen der Sprache in der Datei {filename}: {error}")


def translate_text(text, filename):
    """
    Übersetzt den gegebenen Text in die gewünschte Sprache.

    Args:
        text (str): Der zu übersetzende Text.
        filename (str): Der Name der Datei, die verarbeitet wird.

    Returns:
        str: Der übersetzte Text.
    """
    try:
        text = text

        return text
    except Exception as error:
        log.error(f"Fehler beim Übersetzen der Datei {filename}: {error}")
        return None


def main():
    print(DEEPL_API_KEY)
    try:
        while True:
            check_ordner()
            time.sleep(WARTEZEIT)
    except KeyboardInterrupt:
        log.success(f"Das Programm wurde erfolgreich beendet. Grund: {KeyboardInterrupt}")


# Hauptprogramm
if __name__ == "__main__":
    main()



