#!/usr/bin/env python3
"""
Remove the bookkeeping/scratch files that run_vlbi_pipe.py writes for a run,
so the next invocation starts completely fresh.

This is exactly what run_vlbi_pipe.py already does *automatically* the first
time it doesn't find vp_steps_run.json in the project directory (it wipes
logs/plots/caltables/images and reinitialises the step tracker) - this script
just lets you trigger that on demand, with a preview before anything is
deleted.

Deliberately OUT of scope - never touched, no flag exposes them:
  - Measurement sets and *.flagversions (<project>.ms, *_calibrated.ms, ...)
  - Raw-data safety backups (*_backup.tar) and antab/uvflg/flags/listobs
    products from prepare_data/import_fitsidi
  - vlbi_pipe_inputs.txt / vlbi_pipe_params.json (your configuration)
  - CASA's own casa-<timestamp>.log files
These are either raw data, expensive to regenerate, or your config - if you
really want them gone, remove them by hand.

Usage
-----
# Preview what would be removed (default - nothing is deleted)
./reset_pipeline_run.py /path/to/project/dir

# Actually delete the bookkeeping files + generated per-step job scripts
./reset_pipeline_run.py /path/to/project/dir --yes

# Also empty logs/, plots/, caltables/, images/ (recreated empty) - this is
# the same thing run_vlbi_pipe.py does silently on a fresh start
./reset_pipeline_run.py /path/to/project/dir --products --yes

# Defaults to the current directory if none is given
./reset_pipeline_run.py --yes
"""
import argparse
import glob
import os
import shutil
import sys

# Pure run-state bookkeeping written by run_vlbi_pipe.py / init_pipe_run() -
# always safe to delete, never contains data products.
BOOKKEEPING_FILES = [
    "vp_steps_run.json",
    "vp_gaintables.json",
    "vp_gaintables.last.json",
    "vp_inputs.json",
    "vp_runfile.bash",
]
JOB_SCRIPT_GLOBS = ["job_*.slurm", "job_*.pbs", "job_*.bash"]

# Only touched with --products. These hold real pipeline output (calibration
# tables, images, plots, logs) - still regenerable by rerunning the steps,
# but not free, hence opt-in.
PRODUCT_DIRS = ["logs", "plots", "caltables", "images"]


def find_targets(cwd, include_products):
    files = []
    for f in BOOKKEEPING_FILES:
        p = os.path.join(cwd, f)
        if os.path.exists(p):
            files.append(p)
    for pattern in JOB_SCRIPT_GLOBS:
        files.extend(sorted(glob.glob(os.path.join(cwd, pattern))))

    dirs = []
    if include_products:
        for d in PRODUCT_DIRS:
            p = os.path.join(cwd, d)
            if os.path.isdir(p):
                dirs.append(p)
    return files, dirs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cwd", nargs="?", default=".", help="Pipeline project directory (default: current dir)")
    ap.add_argument("--products", action="store_true",
                     help="Also empty logs/, plots/, caltables/, images/ (recreated empty)")
    ap.add_argument("--yes", action="store_true", help="Actually delete (default is a dry-run preview only)")
    args = ap.parse_args()

    cwd = os.path.abspath(args.cwd)
    if not os.path.isdir(cwd):
        sys.exit("No such directory: %s" % cwd)

    files, dirs = find_targets(cwd, args.products)

    if not files and not dirs:
        print("Nothing to reset in %s" % cwd)
        return

    print("In %s:" % cwd)
    for f in files:
        print("  rm    %s" % os.path.relpath(f, cwd))
    for d in dirs:
        print("  empty %s/" % (os.path.relpath(d, cwd) + os.sep))

    if not args.yes:
        print("\nDry run only - nothing deleted. Re-run with --yes to actually reset.")
        return

    for f in files:
        os.remove(f)
    for d in dirs:
        shutil.rmtree(d)
        os.makedirs(d)

    print("\nDone - next run_vlbi_pipe.py invocation in this directory will start as a fresh run.")


if __name__ == "__main__":
    main()
