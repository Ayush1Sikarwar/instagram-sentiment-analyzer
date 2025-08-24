class DatabaseManager:
    def __init__(self):
        self.rows = []

    def insert_results(self, rows):
        self.rows.extend(rows)

    def get_all(self):
        return self.rows

db = DatabaseManager()
