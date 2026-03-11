import json
import numpy as np


class FaceDatabase:

    def __init__(self, path):

        self.path = path

        self.load()

    def load(self):

        with open(self.path, 'r') as f:

            self.data = json.load(f)

    def match(self, embedding, threshold=0.6):

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