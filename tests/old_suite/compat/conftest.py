def pytest_collection_modifyitems(session, config, items):
    sorted_items = sorted(items, key=lambda item: item.name)
    try:
        items.clear()
    except AttributeError:
        del items[:]
    items.extend(sorted_items)