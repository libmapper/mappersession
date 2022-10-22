from hatchling.builders.hooks.plugin.interface import BuildHookInterface
class CustomHook(BuildHookInterface):
    def initialize(self, version, build_data):
        build_data['pure_python'] = False
        build_data['infer_tag'] = True