from typing import Literal, get_args

# Use for claims
ACCURACY_LITERALS = Literal["accurate", "inaccurate", "mixed", "unable_to_verify", "error"]

# Fact-checking taxonomy
VERDICT_LITERALS = Literal[
    "false",
    "altered",
    "partly_false",
    "missing_context",
    "satire",
    "true",
    "unable_to_verify",
    "not_fact_checkable",
    "not_worth_correcting",
    "error"
]

# LLM-specific versions (exclude "error" so LLMs don't choose it)
# Extract values, filter out "error", and create new Literal
_accuracy_values_for_llm = tuple(v for v in get_args(ACCURACY_LITERALS) if v != "error")
ACCURACY_LITERALS_LLM = Literal[_accuracy_values_for_llm]

_verdict_values_for_llm = tuple(v for v in get_args(VERDICT_LITERALS) if v != "error")
VERDICT_LITERALS_LLM = Literal[_verdict_values_for_llm]

# Default verdict for errors/unmapped cases
DEFAULT_VERDICT = "error"

# Helper constants for verdict checks
POSITIVE_VERDICTS = ["true"]
NEGATIVE_VERDICTS = ["false", "altered", "partly_false", "missing_context"]
NEUTRAL_VERDICTS = ["satire", "unable_to_verify", "not_fact_checkable", "not_worth_correcting", "error"]

# Only auto-trigger note writers for these verdicts
NOTE_WRITING_VERDICTS = ["false", "altered", "partly_false", "missing_context", "satire"]