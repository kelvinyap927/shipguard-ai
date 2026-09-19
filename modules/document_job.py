from modules.attachment_router import route_attachments
from modules.format_router import get_file_type, choose_reader


def build_document_job(email):
    result = route_attachments(email)

    si_file = result["si_file"]
    bl_file = result["bl_file"]

    if result["status"] == "human_review":
        return {
            "email_id": email["email_id"],
            "status": "human_review",
            "reason": "Missing SI or BL attachment",
            "si_file": si_file,
            "bl_file": bl_file
        }

    return {
        "email_id": email["email_id"],
        "status": "ready_for_extraction",

        "si": {
            "path": si_file,
            "type": get_file_type(si_file),
            "reader": choose_reader(si_file)
        },

        "bl": {
            "path": bl_file,
            "type": get_file_type(bl_file),
            "reader": choose_reader(bl_file)
        }
    }