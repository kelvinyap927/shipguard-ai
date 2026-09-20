from modules.pipeline import process_email
from modules.result_aggregator import aggregate_result
from modules.submission_builder import build_submission_record


def process_batch(
    inbox,
    limit=None,
    progress_callback=None,
    start_index=0,
    batch_size=None,
    initial_counts=None,
    initial_failures=0,
):
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

    if initial_counts:
        for key in counts:
            counts[key] = int(initial_counts.get(key, 0))

    pipeline_failures = int(initial_failures)

    start_index = max(0, min(int(start_index), total))

    if batch_size is None:
        end_index = total
    else:
        end_index = min(
            start_index + max(int(batch_size), 1),
            total,
        )

    for position in range(start_index, end_index):
        email = emails[position]

        pipeline_result = process_email(email)

        final_result = aggregate_result(
            email,
            pipeline_result,
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
                    "processed": position + 1,
                    "total": total,
                    "email_id": final_result["email_id"],
                    "status": status,
                    "counts": counts.copy(),
                    "pipeline_failures": pipeline_failures,
                }
            )

    return results
