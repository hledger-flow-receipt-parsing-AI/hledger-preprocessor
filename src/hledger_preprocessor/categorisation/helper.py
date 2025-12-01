from typing import Dict, List


def dict_contains_string(d: Dict, substr: str, case_sensitive: bool) -> bool:
    if case_sensitive:
        return any(substr in str(value) for value in d.values())
    else:
        return any(substr.lower() in str(value).lower() for value in d.values())


def dict_contains_any_of_the_strings(
    *, d: Dict, substrings: str, case_sensitive: bool
) -> bool:
    for some_substr in substrings:
        if dict_contains_string(
            d=d, substr=some_substr, case_sensitive=case_sensitive
        ):
            return True
    return False


def dict_contains_all_of_the_strings(
    *, d: Dict, substrings: List[str], case_sensitive: bool
) -> bool:
    for some_substr in substrings:
        if not dict_contains_string(
            d=d, substr=some_substr, case_sensitive=case_sensitive
        ):
            return False
    return True
