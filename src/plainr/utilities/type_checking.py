"""Type Checking Utilities."""


def is_iterable(obj: object) -> bool:
    """
    Check if an object is iterable.
    """
    return obj is not None and hasattr(obj, "__iter__") and callable(obj.__iter__) # type: ignore

def is_iterable_of_type(
    obj: object, type_: type, *, check_dict_values: bool = False
) -> bool:
    """
    Check if an object is an iterable of a specific type.
    """
    if not is_iterable(obj):
        return False
    if isinstance(obj, list | tuple | set | frozenset):
        return all(isinstance(item, type_) for item in obj)
    if isinstance(obj, dict):
        if check_dict_values:
            return all(isinstance(value, type_) for value in obj.values())
        return all(isinstance(key, type_) for key in obj)
    return False


__all__ = ("is_iterable", "is_iterable_of_type",)
