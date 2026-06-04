import importlib.resources
import sys
import types


class _ShimmedStream:
    def __init__(self, package, resource_name):
        self._package = package
        self._resource_name = resource_name

    def read(self):
        return (
            importlib.resources.files(self._package)
            .joinpath(self._resource_name)
            .read_bytes()
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def resource_stream(package, resource_name):
    if isinstance(package, str):
        mod = sys.modules.get(package)
        if mod is not None and not hasattr(mod, "__path__"):
            package = mod.__package__
    return _ShimmedStream(package, resource_name)


if "pkg_resources" not in sys.modules:
    mod = types.ModuleType("pkg_resources")
    mod.resource_stream = resource_stream
    sys.modules["pkg_resources"] = mod
