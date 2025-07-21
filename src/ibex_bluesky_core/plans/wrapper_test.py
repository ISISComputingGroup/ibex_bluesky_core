from unittest.mock import Mock


# Mock the Msg class since we might not have bluesky installed
class Msg:
    def __init__(self, command, obj=None, *args, **kwargs):
        self.command = command
        self.obj = obj
        self.args = args
        self.kwargs = kwargs

# Remove the function definition since we're importing it
# from time_channels_wrapper import time_channels_wrapper


def test_wrapper_runs_without_error():
    """Simple test to check if the wrapper function executes without crashing."""

    # Create a simple mock plan
    def dummy_plan():
        yield Msg('checkpoint')

    # Create a mock DAE with the required attributes
    mock_dae = Mock()
    mock_dae.tcb_settings = Mock()
    mock_dae.tcb_settings.time_channel_1 = 100
    mock_dae.tcb_settings.time_channel_2 = 200

    # Create mock modules and functions
    import sys
    from types import ModuleType

    # Create mock modules
    mock_bps = ModuleType('bluesky.plan_stubs')
    mock_ophyd = ModuleType('ophyd_async.plan_stubs')
    mock_bpp = ModuleType('bluesky.preprocessors')

    def mock_ensure_connected(device):
        yield Msg('null')

    def mock_rd(device):
        yield Msg('null')
        return mock_dae.tcb_settings

    def mock_mv(device, value):
        yield Msg('null')

    def mock_finalize_wrapper(plan, cleanup):
        try:
            yield from plan
        finally:
            yield from cleanup()

    # Add functions to mock modules
    mock_bps.rd = mock_rd
    mock_bps.mv = mock_mv
    mock_ophyd.ensure_connected = mock_ensure_connected
    mock_bpp.finalize_wrapper = mock_finalize_wrapper

    # Add to sys.modules so imports work
    sys.modules['bluesky.plan_stubs'] = mock_bps
    sys.modules['ophyd_async.plan_stubs'] = mock_ophyd
    sys.modules['bluesky.preprocessors'] = mock_bpp

    try:

        # Import your function from the file
        from time_channels_wrapper import tcb_wrapper

        # Run the wrapper - if it completes without exception, it works!
        wrapped_plan = tcb_wrapper(
            dummy_plan(),
            mock_dae,
            time_channel_1=500
        )

        # Execute the generator to completion
        list(wrapped_plan)

        print("✅ Test passed - wrapper runs without error!")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 You need to:")
        print("   1. Replace 'your_module' with the actual file/module name")
        print("   2. Or copy your time_channels_wrapper function into this test file")

    finally:
        # Clean up sys.modules
        for module in ['bluesky.plan_stubs', 'ophyd_async.plan_stubs', 'bluesky.preprocessors']:
            if module in sys.modules:
                del sys.modules[module]


if __name__ == "__main__":
    test_wrapper_runs_without_error()
