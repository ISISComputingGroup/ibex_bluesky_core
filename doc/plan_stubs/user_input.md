# User input helpers

##  `prompt_user_for_choice`

The {py:obj}`ibex_bluesky_core.plan_stubs.prompt_user_for_choice` plan stub can be used to ask
the user for a constrained set of input choices. This will continue asking if a choice is not valid.

For example:

```python
from ibex_bluesky_core.plan_stubs import prompt_user_for_choice


def plan():
    ...
    answer = yield from prompt_user_for_choice(prompt="Do a or b?", choices=["a", "b"])

    if answer == "a":
        yield from plan_a()
    elif answer == "b":
        yield from plan_b()
```

If a user types "c" in this example as their answer, they will be prompted again.
