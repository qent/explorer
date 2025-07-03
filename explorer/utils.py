def get_file_content(path: str) -> str:
    with open(path, "r", encoding="utf-8") as file:
        return file.read()
