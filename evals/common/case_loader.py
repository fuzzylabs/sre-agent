"""Shared case loader helpers for evaluation suites."""

from pathlib import Path

from pydantic import BaseModel


def load_json_case_models[CaseT: BaseModel](
    cases_dir: Path,
    model_type: type[CaseT],
    *,
    case_id_field: str = "case_id",
) -> list[CaseT]:
    """Load JSON case files into validated Pydantic models.

    Args:
        cases_dir: Directory containing case files.
        model_type: Pydantic model used to validate each case.
        case_id_field: Case id attribute used for duplicate checks.

    Returns:
        Validated case models in stable filename order.
    """
    case_files = sorted(cases_dir.glob("*.json"))
    if not case_files:
        msg = f"No JSON case files found in {cases_dir}."
        raise ValueError(msg)

    cases: list[CaseT] = []
    seen_case_ids: set[str] = set()

    for case_file in case_files:
        case = model_type.model_validate_json(case_file.read_text(encoding="utf-8"))
        _validate_unique_case_id(
            case=case,
            case_file=case_file,
            seen_case_ids=seen_case_ids,
            case_id_field=case_id_field,
        )
        cases.append(case)

    return cases


def _validate_unique_case_id[CaseT: BaseModel](
    case: CaseT,
    case_file: Path,
    seen_case_ids: set[str],
    *,
    case_id_field: str,
) -> None:
    """Ensure case ids are unique across loaded files.

    Args:
        case: The case to validate.
        case_file: The file containing the case.
        seen_case_ids: The set of seen case ids.
        case_id_field: The field containing the case id.
    """
    case_id = getattr(case, case_id_field, None)
    if not isinstance(case_id, str) or not case_id.strip():
        msg = f"Missing or invalid '{case_id_field}' in {case_file}."
        raise ValueError(msg)

    if case_id in seen_case_ids:
        msg = f"Duplicate '{case_id_field}' detected: '{case_id}'."
        raise ValueError(msg)

    seen_case_ids.add(case_id)
