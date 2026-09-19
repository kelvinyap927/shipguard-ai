import os


def get_file_type(file_path):
    if file_path is None:
        return None

    extension = os.path.splitext(file_path)[1].lower()

    return extension.replace(".", "")


def choose_reader(file_path):
    file_type = get_file_type(file_path)

    if file_type == "txt":
        return "text_reader"

    elif file_type == "pdf":
        return "pdf_reader"

    elif file_type == "docx":
        return "docx_reader"

    elif file_type == "xlsx":
        return "xlsx_reader"

    else:
        return "unsupported"