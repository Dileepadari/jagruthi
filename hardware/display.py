import logging
log = logging.getLogger(__name__)
 
_tk = None
 
def _init():
    global _tk
    if _tk is not None:
        return
    try:
        import tkinter as tk
        root = tk.Tk()
        root.title("Jagruthi")
        root.attributes("-fullscreen", True)
        root.configure(bg="black")
        _tk = {"root": root,
               "label": tk.Label(root, text="Jagruthi", font=("Arial", 48),
                                 fg="white", bg="black")}
        _tk["label"].pack(expand=True)
        root.update()
    except Exception as e:
        log.debug("Display init failed: %s", e)
 
def show(text: str):
    _init()
    if _tk:
        _tk["label"].config(text=text)
        _tk["root"].update()
 
def clear():
    show("")