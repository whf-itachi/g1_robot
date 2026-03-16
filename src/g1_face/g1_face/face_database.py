import json
import numpy as np


class FaceDatabase:

    def __init__(self, path):
        self.path = path
        self.data = {"faces": []}  # 初始化为空数据
        self.load()

    def load(self):
        try:
            with open(self.path, 'r') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Face database file not found at {self.path}. Initializing empty database.")
            self.data = {"faces": []}
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in face database file {self.path}: {e}")
            self.data = {"faces": []}
        except Exception as e:
            print(f"Error: Failed to load face database {self.path}: {e}")
            self.data = {"faces": []}

    def match(self, embedding, threshold=0.6):
        try:
            max_sim = 0
            name = None

            for face in self.data["faces"]:
                db = np.array(face["embedding"])

                sim = np.dot(embedding, db) / (
                    np.linalg.norm(embedding) * np.linalg.norm(db)
                )

                if sim > max_sim and sim > threshold:
                    max_sim = sim
                    name = face["name"]

            return name, max_sim
        except KeyError:
            print("Error: Invalid face database format - missing 'faces' key")
            return None, 0
        except Exception as e:
            print(f"Error during face matching: {e}")
            return None, 0