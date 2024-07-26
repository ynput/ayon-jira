# helper functions copied from Applications addons, should be moved from here
# and there to ayon_core/ayon_api or ayon_server
import semver


def sort_versions(addon_versions, reverse=False):
    if semver is None:
        for addon_version in sorted(addon_versions, reverse=reverse):
            yield addon_version
        return

    version_objs = []
    invalid_versions = []
    for addon_version in addon_versions:
        try:
            version_objs.append(
                (addon_version, semver.VersionInfo.parse(addon_version))
            )
        except ValueError:
            invalid_versions.append(addon_version)

    valid_versions = [
        addon_version
        for addon_version, _ in sorted(version_objs, key=lambda x: x[1])
    ]
    sorted_versions = list(sorted(invalid_versions)) + valid_versions
    if reverse:
        sorted_versions = reversed(sorted_versions)
    for addon_version in sorted_versions:
        yield addon_version
