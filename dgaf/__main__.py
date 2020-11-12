import doit
import sys
from . import dodo


doit.doit_cmd.DoitMain(doit.cmd_base.ModuleTaskLoader(
    vars(dodo))).run(sys.argv[1:])
