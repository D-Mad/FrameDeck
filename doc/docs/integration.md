
### Studio Integration
<span style="color:green;">**How to customized based on studio workflows?**</p>

---

<p style="text-align: justify;">
Viewline ships with a lightweight JSON-based implementation that allows the application to run immediately without requiring a production tracking system.
</p>

<p style="text-align: justify;">
In a production environment, studios should replace these JSON examples with queries to their own production management system (for example ShotGrid, FTrack, or an in-house database).
</p>

<p style="text-align: justify;">
The default implementation demonstrates how Viewline expects data to be structured. Only the data retrieval and submission logic needs to be customized. The Viewline itself does not require modification.
</p>


> -  **Projects**
> -  **Versions**
> -  **Review notes**

---

### Projects


>* Projects provide the top-level playlist displayed in the Review Player.
>* The default implementation reads project information from a JSON file.
>* Replace this implementation with your studio's production tracking query.


**Modify the following method:**


```python

# ./scripts/__init__.py

class Projects

    @classmethod
    def get(cls):

```


**Default Example**, the sample project data is located in:

```
./resources/presets/projects.json
```

<span style="color:green;">Use this file as a reference for the expected data structure.</span>

The returned data should contain the information required to populate the Project Browser, such as:

```json
    {
        "type": "Project",
        "id": 358,
        "code": "SCE",
        "name": "Super Chase",
        "created_at": "2026-04-26 10:41:45:PM",
        "image": "..../super_chase.png",
        "sg_description": "viewline test project"
    }
```

<span style="color:magenta;">*Studios are free to include additional metadata if required.*</p>

---


## Versions
>* Versions represent published media available for review.
>* The default implementation reads version information from a JSON file.
>* Studios should replace this implementation with queries to their production tracking system.

**Modify the following method:**

```python

# ./scripts/__init__.py

class Versions

    @classmethod
    def get(cls):

```

**Default Example**, version data is located in:

```
./resources/presets/versions.json
```

<span style="color:green;">Use this file as a reference for the expected data structure.</span>

**The returned data typically includes:**

```json
    {
        "type": "Version",
        "id": 2998,
        "code": "shot-info-101",
        "project": {
            "id": 358,
            "name": "Super Chase",
            "type": "Project"
        },
        "entity": {
            "id": 1999,
            "name": "shot-101",
            "type": "Shot"
        },
        "sg_task": {
            "id": 2999,
            "name": "compositing",
            "type": "Task"
        },
        "sg_status_list": "rev",
        "description": "pipeline test",
        "created_at": "2026-03-16 05:29:13:PM",
        "created_by": {
            "id": 34,
            "name": "Test 0.0.1",
            "type": "User"
        },
        "image": "./render/shot-101/shot-101.png",
        "media": "./render/shot-101/shot-101.mp4"
    },
```


<span style="color:magenta;">*Additional metadata may be included depending on the studio workflow.*</span>

---


## Review Notes
>* Review Notes are used to display existing comments and submit new feedback during playback.
>* The default implementation stores review notes in a JSON file.
>* Production environments should replace this implementation with database queries and write operations.

**1, Modify the following method for <span style="color:green;">query</span> existing review notes:**

```python

# ./scripts/__init__.py

class Review

    @classmethod
    def get(cls):

```

This method should return all review notes associated with the selected version.


**2, Modify the following method for <span style="color:green;">create</span> new review notes:**

```python

# ./scripts/__init__.py

class Review

    @classmethod
    def set(cls):

```

This method should submit newly created review notes to your production tracking system.

The default implementation demonstrates the expected data structure only.


**Default Example**, review data is located in:

```
./resources/presets/reviews.json
```

*Use this file as a reference when integrating with your production database.*

**The review data typically includes:**

``` json

    [
        {
            "id": 10000,
            "type": "Note",
            "subject": "superman's Note on shot-info-101 and  shot-101",
            "content": "test comments",
            "created_at": "2026-07-12 11:46:45:AM",
            "created_by": {
                "id": 101,
                "name": "superman",
                "type": "HumanUser"
            },
            "project": {
                "id": 358,
                "name": "Super Chase",
                "type": "Project"
            },
            "publish_status": "published",
            "sg_review_type": "Comment",
            "sg_status_list": "rev",
            "tasks": [
                {
                    "id": 2999,
                    "name": "compositing",
                    "type": "Task"
                }
            ],
            "attachments": [
                {
                    "id": 10000,
                    "type": "Attachment",
                    "created_at": "2026-07-12 11:46:45:AM",
                    "created_by": {
                        "id": 101,
                        "name": "superman",
                        "type": "HumanUser"
                    },
                    "file_extension": "png",
                    "filename": "1107178060.png",
                    "image": "media/1107178060.png",
                    "project": {
                        "id": 358,
                        "name": "Super Chase",
                        "type": "Project"
                    }
                }
            ],
            "replies": [
                {
                    "id": 10000,
                    "type": "Reply",
                    "content": "ok, I will",
                    "created_at": "2026-07-12 11:46:59:AM",
                    "created_by": {
                        "id": 101,
                        "name": "superman",
                        "type": "HumanUser"
                    },
                    "entity": {
                        "id": 10000,
                        "name": "superman's Note on shot-info-101 and  shot-101",
                        "type": "Note"
                    },
                    "publish_status": "published",
                    "sg_review_type": "Comment",
                    "attachments": []
                },
                {
                    "id": 10001,
                    "type": "Reply",
                    "content": "hi, how it it?",
                    "created_at": "2026-07-12 11:47:36:AM",
                    "created_by": {
                        "id": 101,
                        "name": "superman",
                        "type": "HumanUser"
                    },
                    "entity": {
                        "id": 10000,
                        "name": "superman's Note on shot-info-101 and  shot-101",
                        "type": "Note"
                    },
                    "publish_status": "published",
                    "sg_review_type": "Comment",
                    "attachments": [
                        {
                            "id": 10001,
                            "type": "Attachment",
                            "created_at": "2026-07-12 11:47:36:AM",
                            "created_by": {
                                "id": 101,
                                "name": "superman",
                                "type": "HumanUser"
                            },
                            "file_extension": "png",
                            "filename": "1617757548.png",
                            "image": "media/1617757548.png",
                            "project": {
                                "id": 358,
                                "name": "Super Chase",
                                "type": "Project"
                            }
                        }
                    ]
                }
            ],
            "note_links": [
                {
                    "id": 2998,
                    "name": "shot-info-101",
                    "type": "Version"
                }
            ]
        }
    ]

```

**Data Flow**, The default application follows the workflow below.

```text

    Projects
        │
        ▼
    Project Browser
        │
        ▼
    Versions
        │
        ▼
    Media Player
        │
        ▼
    Review Notes
        │
        ├── Query Existing Notes
        │
        └── Submit New Notes

```

<span style="color:magenta;">Only the highlighted data providers need to be replaced for studio integration.</span>

---

### Why JSON?

The JSON files included with Viewline are intended solely as reference implementations.

They allow developers to:

* Understand the expected data structure.
* Run Viewline without a production tracking system.
* Prototype integrations quickly.
* Test the Review Player independently.

<p style="text-align: justify;">Once integration is complete, the JSON files are no longer required and can be replaced entirely by your production tracking system.</p>


<p style="text-align: justify;">
The default implementation demonstrates how Viewline expects data to be structured. Only the data retrieval and submission logic needs to be customized. The Viewline itself does not require modification.</p>

---

**© Support, subing85@gmail.com.**

---