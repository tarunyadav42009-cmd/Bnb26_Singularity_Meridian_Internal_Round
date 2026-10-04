from collections import Counter
from typing import Dict, List, Any


def evaluate_quorum(
    builder_results: List[Dict[str, Any]],
    required_quorum: int = 2
) -> Dict[str, Any]:

    if not isinstance(
        builder_results,
        list
    ):

        return {
            "status": "REJECT",
            "quorum": 0,
            "required": required_quorum,
            "required_quorum": required_quorum,
            "winning_hash": None,
            "winning_group": [],
            "outliers": [],
            "message": "Invalid builder result list."
        }


    verified_results = [

        result

        for result in builder_results

        if (
            result.get("verified") is True
            and result.get("artifact_hash")
        )
    ]


    if not verified_results:

        return {

            "status": "REJECT",

            "quorum": 0,

            "required":
                required_quorum,

            "required_quorum":
                required_quorum,

            "winning_hash":
                None,

            "winning_group":
                [],

            "outliers":
                [],

            "message":
                "No verified builders available."
        }


    hash_groups = Counter(

        result["artifact_hash"]

        for result in verified_results
    )


    winning_hash, winning_count = (
        hash_groups.most_common(1)[0]
    )


    winning_group = [

        result["builder_id"]

        for result in verified_results

        if result["artifact_hash"]
        == winning_hash
    ]


    outliers = [

        result["builder_id"]

        for result in verified_results

        if result["artifact_hash"]
        != winning_hash
    ]


    if winning_count >= required_quorum:

        status = "ACCEPT"

        if outliers:

            message = (
                "Quorum achieved, but an outlier builder was detected."
            )

        else:

            message = (
                "All verified builders agree."
            )

    else:

        status = "REJECT"

        message = (
            "Required quorum was not achieved."
        )


    return {

        "status":
            status,

        "quorum":
            winning_count,

        "required":
            required_quorum,

        "required_quorum":
            required_quorum,

        "winning_hash":
            winning_hash,

        "winning_group":
            winning_group,

        "outliers":
            outliers,

        "message":
            message
    }