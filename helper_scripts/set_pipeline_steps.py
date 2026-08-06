#!/usr/bin/env python3
"""
Toggle the 0/1 step switches in a vlbi_pipe_inputs.txt file without having
to hand-edit every line.

The pipeline reads step flags with a strict parser (see `headless()` in
VLBI_pipe_functions.py) that only understands bare 0/1/2 integers on
`key = value` lines, so this script edits the file in place line-by-line
and leaves everything else (comments, spacing, parameter_file_path, ...)
untouched.

Examples
--------
# Show the current state of every step
./set_pipeline_steps.py vlbi_pipe_inputs.txt --list

# Turn *only* these steps on, everything else off (most common case)
./set_pipeline_steps.py vlbi_pipe_inputs.txt --only bandpass_cal phase_referencing

# Flip individual steps on/off, leaving the rest exactly as they are
./set_pipeline_steps.py vlbi_pipe_inputs.txt --on qa --off phase_referencing

# Aliases are accepted anywhere a step name is: 'all' (every step) and
# 'phaseref' (every step except the wide-field apply_to_all and mssc steps)
./set_pipeline_steps.py vlbi_pipe_inputs.txt --only phaseref
./set_pipeline_steps.py vlbi_pipe_inputs.txt --only all

# Defaults to ./vlbi_pipe_inputs.txt if no file is given
./set_pipeline_steps.py --only apply_target
"""
import argparse
import re
import sys

# Keep this in sync with the "## Steps to run ##" block in vlbi_pipe_inputs.txt
# and with STEP_KEYS/STEP_ALIASES in run_vlbi_pipe.py.
STEP_KEYS = [
    "prepare_data",
    "import_fitsidi",
    "make_mms",
    "apriori_cal",
    "init_flag",
    "fit_autocorrs",
    "sub_band_delay",
    "bandpass_cal",
    "phase_referencing",
    "apply_target",
    "qa",
    "apply_to_all",
    "mssc",
]

STEP_ALIASES = {
    "all": STEP_KEYS,
    "phaseref": [s for s in STEP_KEYS if s not in ("apply_to_all", "mssc")],
}


def expand_steps(tokens):
    """Expand a list of step names and/or aliases into a deduped list of step names."""
    expanded = []
    for t in tokens:
        for s in STEP_ALIASES.get(t, [t]):
            if s not in expanded:
                expanded.append(s)
    return expanded

LINE_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<key>\w+)(?P<eq>[ \t]*=[ \t]*)(?P<value>[^#\r\n]*?)(?P<tail>[ \t]*(#.*)?)\r?\n?$")


def read_current(path):
    current = {}
    with open(path) as f:
        for line in f:
            m = LINE_RE.match(line)
            if m and m.group("key") in STEP_KEYS:
                current[m.group("key")] = m.group("value").strip()
    return current


def apply_changes(path, changes):
    with open(path) as f:
        lines = f.readlines()

    touched = set()
    new_lines = []
    for line in lines:
        m = LINE_RE.match(line)
        if m and m.group("key") in changes:
            key = m.group("key")
            new_line = "%s%s%s%s%s\n" % (
                m.group("indent"), key, m.group("eq"), changes[key], m.group("tail")
            )
            new_lines.append(new_line)
            touched.add(key)
        else:
            new_lines.append(line)

    missing = set(changes) - touched
    if missing:
        sys.exit("Error: step(s) not found in %s: %s" % (path, ", ".join(sorted(missing))))

    with open(path, "w") as f:
        f.writelines(new_lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs_file", nargs="?", default="vlbi_pipe_inputs.txt",
                     help="Path to vlbi_pipe_inputs.txt (default: %(default)s)")
    step_choices = STEP_KEYS + list(STEP_ALIASES)
    ap.add_argument("--only", nargs="+", metavar="STEP", choices=step_choices,
                     help="Set exactly these steps (or aliases: %s) to 1 and all other steps to 0" % ", ".join(STEP_ALIASES))
    ap.add_argument("--on", nargs="+", metavar="STEP", choices=step_choices,
                     help="Set these steps (or aliases) to 1, leaving other steps untouched")
    ap.add_argument("--off", nargs="+", metavar="STEP", choices=step_choices,
                     help="Set these steps (or aliases) to 0, leaving other steps untouched")
    ap.add_argument("--list", action="store_true", help="Print current step values and exit")
    args = ap.parse_args()

    if args.list:
        current = read_current(args.inputs_file)
        width = max(len(k) for k in STEP_KEYS)
        for k in STEP_KEYS:
            print("%-*s = %s" % (width, k, current.get(k, "?")))
        return

    if not (args.only or args.on or args.off):
        ap.error("nothing to do - pass --only/--on/--off, or --list to inspect the file")

    only = expand_steps(args.only) if args.only else None
    on = expand_steps(args.on) if args.on else None
    off = expand_steps(args.off) if args.off else None

    changes = {}
    if only:
        for k in STEP_KEYS:
            changes[k] = "1" if k in only else "0"
    if on:
        for k in on:
            changes[k] = "1"
    if off:
        for k in off:
            changes[k] = "0"

    apply_changes(args.inputs_file, changes)

    current = read_current(args.inputs_file)
    width = max(len(k) for k in STEP_KEYS)
    for k in STEP_KEYS:
        marker = " <-" if k in changes else ""
        print("%-*s = %s%s" % (width, k, current.get(k, "?"), marker))


if __name__ == "__main__":
    main()
