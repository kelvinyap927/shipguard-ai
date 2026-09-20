from modules.pipeline import process_email
from modules.result_aggregator import aggregate_result


def process_batch(inbox, limit=None):

    results = []

    for index, email in enumerate(inbox):

        if limit is not None and index >= limit:
            break

        pipeline_result = process_email(email)

        final_result = aggregate_result(
            email,
            pipeline_result
        )

        results.append(final_result)

    return results
