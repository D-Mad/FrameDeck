import os
import webbrowser


def hasPathExists(filepath):
    if not filepath:
        return None

    absfilepath = os.path.expandvars(filepath)

    return os.path.exists(absfilepath)


def openUrl(path):
    webbrowser.open(path)


if __name__ == "__main__":
    pass
