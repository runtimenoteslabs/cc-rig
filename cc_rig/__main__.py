"""Allow running cc-rig as `python -m cc_rig`."""

import sys

from cc_rig.cli import main

sys.exit(main())
