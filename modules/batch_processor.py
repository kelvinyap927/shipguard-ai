from modules.pipeline import process_email
from modules.result_aggregator import aggregate_result
from modules.submission_builder import build_submission_record


def process_batch(inbox, limit=None, progress_callback=None):

    emails = list(inbox)

    if limit is not None:
        emails = emails[:limit]

    total = len(emails)
    results = []

    counts = {
        "OK": 0,
        "MISMATCH": 0,
        "NEEDS_REVIEW": 0,
    }

    pipeline_failures = 0

    for index, email in enumerate(emails, start=1):

        pipeline_result = process_email(email)

        final_result = aggregate_result(
            email,
            pipeline_result
        )

        results.append(final_result)

        submission_record = build_submission_record(
            final_result
        )

        status = submission_record["status"]

        if status in counts:
            counts[status] += 1

        if pipeline_result.get("status") == "failed":
            pipeline_failures += 1

        if progress_callback is not None:
            progress_callback(
                {
                    "processed": index,
                    "total": total,
                    "email_id": final_result["email_id"],
                    "status": status,
                    "counts": counts.copy(),
                    "pipeline_failures": pipeline_failures,
                }
            )

    return results
