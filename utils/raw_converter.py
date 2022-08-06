from typing import Dict, Union


def upref_to_dict(upref: int) -> Dict[str, Union[int, bool]]:
    if upref == 0:
        return {
            "theme": 0,
            "show-debug-stuff-for-realz": 0
        }
    else:
        sref = str(upref)
        lref = list(sref)
        constructor = {}  # Constructor i hardly know'er
        keys = ["theme", "show-debug-stuff-for-realz"]
        for value, index in zip(lref, range(2)):
            if not isinstance(value, int):
                raise TypeError("Parameter 'value' should be type 'int', is type %s" % type(value))
            constructor[keys[index]] = value
        if len(constructor.keys()) != len(keys):  # The constructor wasn't built properly
            raise ValueError(
                "Constructor dictionary length ({}) did not match length of keys list ({})"
                .format(
                    len(constructor.keys()),
                    len(keys)
                )
            )
        return constructor
