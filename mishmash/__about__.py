import dataclasses

project_name = "MishMash"
version      = "0.3b14"
release_name = ""
author       = "Travis Shirk"
author_email = "travis@pobox.com"
years        = "2013-2019"

@dataclasses.dataclass
class Version:
    major: int
    minor: int
    maint: int
    release: str
    release_name: str

version_info = Version(0, 3, 0, "b14", "")
