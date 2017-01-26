def pytest_collection_modifyitems(session, config, items):
    sorted_items = sorted(items, key=lambda item: item.name)
    items.clear()
    items.extend(sorted_items)