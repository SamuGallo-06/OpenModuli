import os
import xml.etree.ElementTree as ET

class Settings():
    settings = {}
        
    def load(self):
        settings_path = os.path.join("settings", "settings.xml")
        print(f"[INFO]: Loading settings from {settings_path}...")
        settings_tree = ET.parse(settings_path)
        settings_root = settings_tree.getroot()
        self.settings.clear()
        
        for child in settings_root:
            print(child.tag)
            self.settings[child.tag] = {}
            for subchild in child:
                    print(f"    {subchild.tag}: {subchild.text}")
                    self.settings[child.tag][subchild.tag] = subchild.text

    def save(self):
        settings_path = os.path.join("settings", "settings.xml")
        print(f"[INFO]: Saving settings to {settings_path}...")

        settings_tree = ET.parse(settings_path)
        settings_root = settings_tree.getroot()

        for child in settings_root:
            child_values = self.settings.get(child.tag, {})
            if not isinstance(child_values, dict):
                continue

            for subchild in child:
                if subchild.tag in child_values:
                    value = child_values[subchild.tag]
                    subchild.text = "" if value is None else str(value)

        settings_tree.write(settings_path, encoding="utf-8", xml_declaration=True)
    