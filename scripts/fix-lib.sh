#!/usr/bin/env bash
set -e
export MM="mishmash -c /opt/unsonic/mishmash.ini"

cat <<EOF | $MM split-artists -L Music "The Giraffes"
2
Brooklyn
NY
USA
Seattle
WA
USA
1
1
1
2
EOF
