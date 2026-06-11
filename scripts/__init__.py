"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.
Author: Subin. Gopi (subing85@gmail.com).
Description: Review Player playlist customization module.
WARNING! All changes made in this file will be lost when recompiling source file!

    - This module provides project and version data providers used by the Review Player playlist system.
    - The playlist module is intentionally designed as a customization layer for studio pipelines.

Studios can replace the default implementations with:
    - ShotGrid queries
    - FTrack queries
    - Database queries
    - REST API integrations
    - Asset management systems

Default Behavior:
    The current implementation loads example JSON preset
    data from:
        resources/presets/

Modules:
    Projects:
        Provides project playlist data.

    Versions:
        Provides version/media playlist data.

Architecture:
    Project
        ↓
    Versions
        ↓
    Media Path
        ↓
    Playback System

Notes:
    This module acts as the integration entry point
    between the review player and studio production
    tracking systems.
"""

from __future__ import absolute_import

import resources


class Projects(object):
    """Project playlist data provider.

    This class provides project-level playlist data used by the Review Player UI.

    Responsibilities:
        - Return available projects
        - Provide playlist-compatible project data
        - Serve as studio integration entry point

    Notes:
        Studios are expected to replace this implementation with production tracking queries.

    Supported Integrations:
        - ShotGrid
        - FTrack
        - Kitsu
        - Custom database
        - REST API

    Example:
        >>> projects = Projects.get()
    """

    @classmethod
    def get(cls):
        """Return project playlist data.

        Returns:
            list:
                Project playlist data.

        Notes:
            This implementation loads example preset data
            from:
                resources/presets/projects.json

            Replace this method with:
                - Database queries
                - API requests
                - ShotGrid queries
                - FTrack queries

        Example:
            >>> projects = Projects.get()
        """

        # Load Example Project Preset Data
        result = resources.getPreset("projects")

        return result


class Versions(object):
    """Version/media playlist data provider.

    This class provides media/version data associated with projects.

    Responsibilities:
        - Return version/media data
        - Filter project versions
        - Sort versions by creation date
        - Provide playback-ready media data

    Notes:
        Studios should replace this implementation with production tracking system queries.

    Example:
        >>> versions = Versions.get(project)
    """

    @classmethod
    def get(cls, project):
        """Return versions/media data for project.

        Args:
            project (dict):
                Project dictionary.

        Returns:
            list:
                Filtered and sorted version list.

        Notes:
            This implementation loads example preset data
            from:
                resources/presets/versions.json

            Replace this method with:
                - ShotGrid Version queries
                - FTrack AssetVersion queries
                - Database queries
                - REST API integrations

        Example:
            >>> versions = Versions.get(project)
        """

        # Load Example Version Preset Data
        versions = resources.getPreset("versions")

        # Filter Versions By Project
        project_versions = list(
            filter(lambda x: x.get("project") and x["project"]["id"] == project["id"], versions)
        )

        # Sort Versions By Creation Date
        result = sorted(project_versions, key=lambda k: (k["created_at"]), reverse=True)

        return result


class Submit(object):

    @classmethod
    def set(cls, project):
        """Return versions/media data for project.

        Args:
            project (dict):
                Project dictionary.

        Returns:
            list:
                Filtered and sorted version list.

        Notes:
            This implementation loads example preset data
            from:
                resources/presets/versions.json

            Replace this method with:
                - ShotGrid Version queries
                - FTrack AssetVersion queries
                - Database queries
                - REST API integrations

        Example:
            >>> versions = Versions.get(project)
        """

        # Load Example Version Preset Data
        versions = resources.getPreset("versions")

        # Filter Versions By Project
        project_versions = list(
            filter(lambda x: x.get("project") and x["project"]["id"] == project["id"], versions)
        )

        # Sort Versions By Creation Date
        result = sorted(project_versions, key=lambda k: (k["created_at"]), reverse=True)

        return result

    @classmethod
    def get(cls, version):
        pass


if __name__ == "__main__":
    pass
