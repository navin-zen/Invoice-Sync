"""
Task scheduler.

Ensures fairness (not in any theoretical sense) between Customers. Ensures
that one or more customers do not hog all resources. We have a limit on the
number of tasks that can run simultaneously. This limit mainly comes from
the number of database connections that we have and the read/write
bandwidth that our DB can support. We want to distribute these task slots
between customers.
"""

from collections import Counter


def choose_tasks(max_slots, current_tasks, waiting_tasks):
    """
    Choose tasks for execution.

    :param: max_slots - The maximum number of tasks that we can run simultaneously
    :param: current_tasks - List of tasks that are currently running
    :param: waiting_tasks - List of tasks that are waiting to be run

    Each task is a 3-tuple: (schema_name, task_uuid, create_date)

    Returns the list of waiting tasks that are chosen for running.
    """
    if not waiting_tasks:
        return []
    available_slots = max(max_slots - len(current_tasks), 0)
    if available_slots <= 0:
        return []
    if len(waiting_tasks) <= available_slots:
        return waiting_tasks
    if len({schema_name for (schema_name, _, _) in waiting_tasks}) <= 1:
        # Only one customer is waiting
        return waiting_tasks[:available_slots]
    # Maintain counts of schema_name -> # tasks
    counts = Counter(schema_name for (schema_name, _, _) in current_tasks)  # schema_name -> # tasks

    def key(o):
        (schema_name, uuid, create_date) = o
        return (counts.get(schema_name, 0), create_date)

    # Sort waiting_tasks one time in what we think will be favorable order
    waiting_tasks = sorted(waiting_tasks, key=key)
    chosen_ones = set()
    for level in range(max_slots):
        if (available_slots <= 0) or (not waiting_tasks):
            break
        to_be_removed = set()
        for t in waiting_tasks:
            if available_slots <= 0:
                break
            (schema_name, uuid, _) = t
            if counts.get(schema_name, 0) <= level:
                to_be_removed.add(t)
                chosen_ones.add(t)
                counts.update([schema_name])
                available_slots -= 1
        waiting_tasks = [t for t in waiting_tasks if (t not in to_be_removed)]
    return list(chosen_ones)
