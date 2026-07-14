"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./scripts/__init__.py

Description:
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

import utils
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
        reviews_path = utils.frameDeckPath(subfolder="schemas")
        projects_file = utils.pathResolver(reviews_path, filename="projects.json")

        projects_data_list = utils.readJsonFile(projects_file)

        if not projects_data_list:
            projects_data_list = utils.redirectPreset("projects", reviews_path)
            utils.writeJsonFile(projects_data_list, projects_file, indent=4)

        for projects_data in projects_data_list:
            projects_data["image"] = utils.pathResolver(
                reviews_path, filename=projects_data["image"]
            )

        # Sort Versions By Creation Date
        result = sorted(projects_data_list, key=lambda k: (k["created_at"]), reverse=True)

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
        reviews_path = utils.frameDeckPath(subfolder="schemas")
        versions_file = utils.pathResolver(reviews_path, filename="versions.json")
        versions_data_list = utils.readJsonFile(versions_file)

        if not versions_data_list:
            versions_data_list = utils.redirectPreset("versions", reviews_path)

            utils.writeJsonFile(versions_data_list, versions_file, indent=4)

        for versions_data in versions_data_list:
            versions_data["image"] = utils.pathResolver(
                reviews_path, filename=versions_data["image"]
            )

            versions_data["media"] = utils.pathResolver(
                reviews_path, filename=versions_data["media"]
            )

        # Filter Versions By Project
        versions_data = list(
            filter(
                lambda x: x.get("project") and x["project"]["id"] == project["id"],
                versions_data_list,
            )
        )

        # Sort Versions By Creation Date
        result = sorted(versions_data, key=lambda k: (k["created_at"]), reverse=True)

        return result


class Review(object):

    @classmethod
    def set(cls, context):
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

        username = utils.getUsername()
        created_by = {"id": 101, "name": username, "type": "HumanUser"}
        created_at = utils.getDateTimes(times=None)
        project = context["version"]["project"]
        version = context["version"]

        reviews_path = utils.frameDeckPath(subfolder="schemas")

        # Attachments
        attachment_file = utils.pathResolver(reviews_path, filename="attachment.json")
        attachment_data_list = utils.readJsonFile(attachment_file) or list()

        attachment_contents = list()

        for index, attachment in enumerate(context["attachments"]):
            numericId = utils.numericId()
            extension = utils.fileExtension(attachment)
            filepath = utils.pathResolver(
                reviews_path, folders=["media"], filename=f"{numericId}.{extension}"
            )
            utils.copyFile(attachment, filepath)
            relative_path = f"media/{numericId}.{extension}"

            id = ((attachment_data_list[-1]["id"] + 1) if attachment_data_list else 10000) + index

            content = {
                "id": id,
                "type": "Attachment",
                "created_at": created_at,
                "created_by": created_by,
                "file_extension": extension,
                "filename": f"{numericId}.{extension}",
                "image": relative_path,
                "project": project,
            }

            attachment_contents.append(content)

        attachment_data_list = attachment_data_list + attachment_contents
        utils.writeJsonFile(attachment_data_list, attachment_file, indent=4)

        # Notes
        note_file = utils.pathResolver(reviews_path, filename="note.json")
        note_data_list = utils.readJsonFile(note_file) or list()

        matched_note = next(
            filter(
                lambda x: any(
                    link["type"] == "Version" and link["id"] == version["id"]
                    for link in x.get("note_links", [])
                ),
                note_data_list,
            ),
            None,
        )

        if matched_note:  # Create replay
            date_file = utils.pathResolver(reviews_path, filename="reply.json")
            reply_data_list = utils.readJsonFile(date_file) or list()

            content = {
                "id": (reply_data_list[-1]["id"] + 1) if reply_data_list else 10000,
                "type": "Reply",
                "content": context["message"],
                "created_at": created_at,
                "created_by": created_by,
                "entity": {
                    "id": matched_note["id"],
                    "name": matched_note["subject"],
                    "type": "Note",
                },
                "publish_status": "published",
                "sg_review_type": context["reviewType"]["value"],
                "attachments": attachment_contents,
            }

            # Update status in note data
            matched_note["sg_status_list"] = context["status"]["value"]
            matched_note["replies"].append(content)

            utils.writeJsonFile(note_data_list, note_file, indent=4)

            content_list = reply_data_list + [content]

        else:  # Create note
            content = {
                "id": (note_data_list[-1]["id"] + 1) if note_data_list else 10000,
                "type": "Note",
                "subject": f"{username}'s Note on {context['version']['code']} and  {context['version']['entity']['name']}",
                "content": context["message"],
                "created_at": created_at,
                "created_by": created_by,
                "project": project,
                "publish_status": "published",
                "sg_review_type": context["reviewType"]["value"],
                "sg_status_list": context["status"]["value"],
                "tasks": [version["sg_task"]],
                "attachments": attachment_contents,
                "replies": list(),
                "note_links": [{"id": version["id"], "name": version["code"], "type": "Version"}],
            }
            date_file = note_file
            content_list = note_data_list + [content]

        utils.writeJsonFile(content_list, date_file, indent=4)

        # Update version status
        versions_file = utils.pathResolver(reviews_path, filename="versions.json")
        versions_data_list = utils.readJsonFile(versions_file)

        current_version = next(filter(lambda x: x["id"] == version["id"], versions_data_list), None)
        current_version["sg_status_list"] = context["status"]["value"]

        utils.writeJsonFile(versions_data_list, versions_file, indent=4)

        version["sg_status_list"] = context["status"]["value"]

        message = f"created {content['type']} {content['sg_review_type']} ( {content['id']} )"

        return True, message

    @classmethod
    def get(cls, version, reverse=False):

        reviews_path = utils.frameDeckPath(subfolder="schemas")
        note_file = utils.pathResolver(reviews_path, filename="note.json")

        note_data_list = utils.readJsonFile(note_file) or list()

        review_notes = list(
            filter(
                lambda x: any(
                    link["type"] == "Version" and link["id"] == version["id"]
                    for link in x["note_links"]
                ),
                note_data_list,
            )
        )

        if not review_notes:
            return False, None

        result = list()

        for review_note in review_notes:
            node_copy = review_note.copy()
            node_copy.pop("attachments")
            node_copy.pop("replies")

            for attachment in review_note["attachments"]:
                attachment["image"] = utils.pathResolver(reviews_path, filename=attachment["image"])

            node_content = [[node_copy, review_note["attachments"]]]

            for reply in review_note["replies"]:
                reply_copy = reply.copy()
                reply_copy.pop("attachments")

                for attachment in reply["attachments"]:
                    attachment["image"] = utils.pathResolver(
                        reviews_path, filename=attachment["image"]
                    )

                reply_content = [reply_copy, reply["attachments"]]

                node_content.append(reply_content)

            result.append(node_content)

        return True, result


if __name__ == "__main__":
    pass
