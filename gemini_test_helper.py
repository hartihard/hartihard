"""Testdatei fuer Gemini-Review (wird nach dem Test wieder entfernt)."""
import subprocess


def durchschnitt(werte):
    return sum(werte) / len(werte)


def datei_loeschen(name):
    subprocess.run("rm -rf " + name, shell=True)
