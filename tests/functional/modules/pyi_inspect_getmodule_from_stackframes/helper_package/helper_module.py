import inspect


def test_call_chain():
    modules = []
    for idx, frame_info in enumerate(inspect.stack()):
        #print(frame_info)
        module = inspect.getmodule(frame_info[0])
        assert module, f"Failed to get module for frame #{idx}: {frame_info}"
        modules.append(module)
    return modules
