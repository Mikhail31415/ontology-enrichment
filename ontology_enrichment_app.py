import tkinter as tk

from src.config import configure_logging, get_yaml_configs
from src.gui.main_window import MainWindow


def main():
    configure_logging(get_yaml_configs()['logging'])
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()


# C:\Users\Михаил\Desktop\ontology\geo.owl
# C:\Users\Михаил\Desktop\ontology\geoTest.owl
# https://ru.wikipedia.org/wiki/%D0%93%D0%B5%D0%BE%D0%B3%D1%80%D0%B0%D1%84%D0%B8%D1%8F_%D0%9A%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D1%82%D0%B0%D0%BD%D0%B0
# pyinstaller --onedir -w ontology_enrichment_app.py --add-data "resources/application.yaml;resources" --add-data ".venv/Lib/site-packages/owlready2/pellet;owlready2/pellet" --hidden-import tiktoken.load --add-data ".venv/Lib/site-packages/tiktoken_ext/openai_public.py;tiktoken_ext" --icon=resources/icon.ico
