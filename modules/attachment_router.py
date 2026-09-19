def route_attachments(email):
    attachments = email["attachments"]

    si_file = None
    bl_file = None
    other_files = []

    for attachment in attachments:
        filename = attachment.lower()

        if "_si." in filename:
            si_file = attachment

        elif "_bl." in filename:
            bl_file = attachment

        else:
            other_files.append(attachment)

    if si_file is None or bl_file is None:
        status = "human_review"
    else:
        status = "ready"

    return {
        "si_file": si_file,
        "bl_file": bl_file,
        "other_files": other_files,
        "status": status
    }