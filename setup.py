#!/usr/bin/env python
from parcyl import Setup, find_package_files

setup = Setup(info_file="mishmash/__about__.py").with_packages("./", exclude=["tests", "tests.*"])
setup(package_dir={"": "."},
      zip_safe=False,
      platforms=["Any"],
      test_suite="./tests",
      include_package_data=True,
      package_data={
          "mishmash": ["alembic.ini"] + find_package_files("mishmash/alembic"),
          "mishmash.web": find_package_files("mishmash/web/static", "../..")
                          + find_package_files("mishmash/web/templates", "../.."),
          },
      entry_points={
                  "console_scripts": [
                      "mishmash = mishmash.__main__:app.run",
                  ]
              },
)
