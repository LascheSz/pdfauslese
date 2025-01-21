import os
import shutil

# Konstanten
ORDNER = "C:/Users/em/Desktop/Test/"
FINISHED = os.path.join(ORDNER, "finished")


# Funktion zum Verschieben der Dateien
def movefiles():
    files_list = os.listdir(FINISHED)
    for filename in files_list:
        shutil.move(os.path.join(FINISHED, filename), os.path.join(ORDNER, filename))
        print(f"Datei {filename} wurde verschoben")


if __name__ == "__main__":
    movefiles()