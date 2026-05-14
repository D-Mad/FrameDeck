import re


def extract_frame_number(path):
    """
    Extract frame number from path.
    """

    result = re.search(r"\.(\d+)\.", path)

    if not result:
        return None

    return int(result.group(1))


def get_sequence_path(path):
    """
    Convert sequence file into grouped pattern.

    Example:
        shot.1001.exr
        ->
        shot.%04d.exr
    """

    result = re.search(r"(.*)\.(\d+)\.(\w+)$", path)

    if not result:
        return path

    prefix = result.group(1)

    frame = result.group(2)

    extension = result.group(3)

    padding = len(frame)

    return f"{prefix}.%0{padding}d.{extension}"
