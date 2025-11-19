import hashlib
import json
import logging
from collections import defaultdict
from pathlib import Path
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)
logging.basicConfig()

# Type alias for the parse_log return type to keep signatures short
ParseResult = Tuple[Optional[Union[str, "NeuroDiscoveryBenchOutput"]], int]


class NeuroDiscoveryBenchOutput(BaseModel):
    """Pydantic model for the expected output payload.

    Currently only defines `hypothesis` but may be extended later.
    """

    hypothesis: str


def hash_json_content(file_path: str) -> Optional[str]:
    """Return a stable hash for the JSON content of `file_path`.

    Returns None on failure and logs the exception.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        normalized = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    except Exception as e:
        logger.debug("Error reading %s: %s", file_path, e)
        return None


def find_duplicate_jsons(directory: Union[str, Path]) -> Dict[str, List[str]]:
    """Find duplicate JSON files in `directory` by content hash.

    Returns a mapping from content-hash -> list of file paths
    (only when length > 1).
    """
    json_files = list(Path(directory).rglob("*.json"))
    hash_to_files: Dict[str, List[str]] = defaultdict(list)

    for file_path in json_files:
        content_hash = hash_json_content(file_path)
        if content_hash:
            hash_to_files[content_hash].append(str(file_path))

    duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}

    if duplicates:
        logger.info("Found duplicate JSON files")
        for files in duplicates.values():
            logger.info("Duplicate group: %s", files)
    else:
        logger.debug("No duplicate JSON files found in %s", directory)

    return duplicates


def extract_json_from_response(response: str) -> dict[str, Any] | None:
    """Extract JSON from a response string.  Tries to be flexible with format,
    allowing other text around the json.  Returns None if no valid JSON."""
    json_start = response.find("{")
    json_end = response.rfind("}") + 1
    if json_start == -1 or json_end == -1:
        return None

    try:
        return json.loads(response[json_start:json_end])
    except json.JSONDecodeError:
        try:
            return json.loads(response[json_start + 1 : json_end - 1])
        except json.JSONDecodeError:
            print(
                f"Could not decode JSON from response: {response[json_start:json_end]}"
            )
        return None


def extract_output(text_out: str) -> Union[NeuroDiscoveryBenchOutput, str]:
    """Extract a structured `NeuroDiscoveryBenchOutput` from `text_out`.

    Returns the parsed model on success, otherwise returns a string
    describing the (possibly partial) extracted output.
    """
    dict_out = extract_json_from_response(text_out)
    if isinstance(dict_out, dict):
        try:
            return NeuroDiscoveryBenchOutput.model_validate(dict_out)
        except Exception as e:
            logger.debug("Validation into NeuroDiscoveryBenchOutput failed", e)
            logger.debug("data=%s", dict_out)
            return json.dumps(dict_out)
    return str(text_out)


def parse_log(log_file: str) -> ParseResult:
    """Parse a log file and return the last output if found.

    The function handles two common log formats:
    - DV Log: A JSON file containing a top-level `logs` list where each entry is a dict
      with keys like `source` and `content`.
    - Agent Log: Newline-delimited JSON log lines where each line is a JSON object and
      the relevant payload is under the `message` key.

    Returns a tuple `(result, success_flag)` where `result` is either
    a `NeuroDiscoveryBenchOutput`, a string (partial or raw), or `None` if
    nothing was found. `success_flag` is `1` when the returned result is a
    `NeuroDiscoveryBenchOutput`, otherwise `0`.
    """
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception as e:
        logger.error("Failed to read log file %s: %s", log_file, e)
        return None, 0

    if not raw:
        return None, 0

    message_with_hypo = None
    try:
        data = json.loads(raw)
        data = data["logs"]
        for msg in reversed(data):
            if msg["source"] == "MagenticOneOrchestrator":
                message_with_hypo = msg["content"]
                break

    except json.JSONDecodeError:
        try:
            data = raw.split("\n")
            for line in reversed(data[:-2]):
                message_with_hypo = json.loads(json.loads(line)["message"])
                if isinstance(
                    extract_output(message_with_hypo), NeuroDiscoveryBenchOutput
                ):
                    break

        except Exception as e:
            print(f"Error while parsing log (parse_log): {e}")

    if message_with_hypo is None:
        return message_with_hypo, 0

    result = extract_output(str(message_with_hypo))
    if isinstance(result, str):
        return result, 0
    if isinstance(result, NeuroDiscoveryBenchOutput):
        return result, 1
