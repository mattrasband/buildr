class BuildError(Exception):
    """Defines an error during the process, this doesn't mean
    anything failed but instead that either a precondition failed
    or a pre-build item."""


class BuildFailure(Exception):
    """Defines a failure in a build step,"""
