#!/usr/bin/env bash
#
# Download data for any EVN experiment from the JIVE archive.
#
# Experiment codes and dates are looked up automatically from the EVN VO
# TAP service (https://evn-vo.jive.nl/tap), so you only need to know the
# project code (e.g. ER047, N14C3, ES072) - not the exact "_YYMMDD"
# suffix used by the archive.
#
# Usage (interactive):
#   ./download_evn.sh
#
# Usage (non-interactive):
#   ./download_evn.sh -c PROJECT [-e EPOCH|ALL] [-a] [-p] [-P] [-d wget|axel] [-j N]
#
#   -c PROJECT Project code, e.g. ER047, N14C3, ES072 (required for
#              non-interactive use)
#   -e EPOCH   Segment/epoch obs_id as reported by the archive (e.g. ER047A),
#              or ALL for every segment (default: ALL)
#   -a         Download ALL fits files instead of just the first source
#              (<prefix>_1_1*). First-source-only downloads go to
#              X/phsref_data; ALL-fits downloads go to X/data.
#   -p         Also download the pipeline data (from /pipe) into
#              X/evn_pipe
#   -P         Only download the pipeline data (skip /fits entirely)
#   -d DOWNLOADER  Download engine: "wget" (default) or "axel". axel opens
#              multiple connections per file for faster transfers; it
#              runs from vlbi_pipeline/singularity_images/axel.sif via
#              apptainer/singularity if not installed on the host.
#   -j N       Number of connections per file when using axel (default 8)
#   -h         Show this help
#
# Examples:
#   ./download_evn.sh -c ER047                     # every segment, first source only
#   ./download_evn.sh -c ER047 -e ER047C            # segment C only
#   ./download_evn.sh -c ER047 -e ER047C -a         # all fits files for segment C
#   ./download_evn.sh -c ER047 -a -p                # all fits + pipeline, every segment
#   ./download_evn.sh -c N14C3 -P                   # pipeline data only
#   ./download_evn.sh -c ER047 -e ER047C -a -d axel -j 12

set -euo pipefail

TAP_URL="https://evn-vo.jive.nl/tap/sync"
BASE_URL="https://archive.jive.eu/exp"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AXEL_SIF="${SCRIPT_DIR}/vlbi_pipeline/singularity_images/axel.sif"

usage() {
    sed -n '2,39p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
}

PROJECT=""
EPOCH="ALL"
EPOCH_SET=0
ALL_FITS=0
DO_PIPE=0
PIPE_ONLY=0
DOWNLOADER="wget"
DOWNLOADER_SET=0
AXEL_CONNECTIONS=8

while getopts ":c:e:apPhd:j:" opt; do
    case "$opt" in
        c) PROJECT="${OPTARG^^}" ;;
        e) EPOCH="${OPTARG^^}"; EPOCH_SET=1 ;;
        a) ALL_FITS=1 ;;
        p) DO_PIPE=1 ;;
        P) PIPE_ONLY=1 ;;
        d) DOWNLOADER="${OPTARG,,}"; DOWNLOADER_SET=1 ;;
        j) AXEL_CONNECTIONS="${OPTARG}" ;;
        h) usage ;;
        \?) echo "Unknown option: -$OPTARG" >&2; usage ;;
        :) echo "Option -$OPTARG requires an argument" >&2; usage ;;
    esac
done

if [[ "$DOWNLOADER" != "wget" && "$DOWNLOADER" != "axel" ]]; then
    echo "Error: -d must be 'wget' or 'axel', got '$DOWNLOADER'" >&2
    exit 1
fi

# Interactive project-code prompt if not supplied on the command line
if [[ -z "$PROJECT" ]]; then
    read -rp "Enter EVN project code (e.g. ER047, N14C3): " PROJECT
fi
PROJECT="${PROJECT^^}"
if [[ ! "$PROJECT" =~ ^[A-Z0-9]+$ ]]; then
    echo "Error: project code must be alphanumeric, got '$PROJECT'" >&2
    exit 1
fi

# Look up every archived segment for this project via the EVN VO TAP service,
# mapping each segment's obs_id (e.g. ER047A) to its dated archive directory
# name (e.g. ER047A_190308), which is embedded in the dataset access_url.
echo "Looking up archived segments for project '$PROJECT'..." >&2
declare -A EXP_CODE=()
while IFS=, read -r obs_id access_url; do
    [[ "$obs_id" == "obs_id" || -z "$obs_id" ]] && continue
    if [[ -z "${EXP_CODE[$obs_id]:-}" ]]; then
        dated="$(grep -oE "${obs_id}_[0-9]{6}" <<< "$access_url" | head -1)"
        [[ -n "$dated" ]] && EXP_CODE["$obs_id"]="$dated"
    fi
done < <(curl -sL "$TAP_URL" \
    --data-urlencode "REQUEST=doQuery" \
    --data-urlencode "LANG=ADQL" \
    --data-urlencode "QUERY=SELECT obs_id, access_url FROM evn.main WHERE obs_id LIKE '${PROJECT}%'" \
    --data-urlencode "FORMAT=csv")

if [[ ${#EXP_CODE[@]} -eq 0 ]]; then
    echo "Error: no archived segments found for project '$PROJECT'." >&2
    echo "Check the code, or browse https://archive.jive.eu/scripts/portal.php" >&2
    exit 1
fi

mapfile -t AVAILABLE_EPOCHS < <(printf '%s\n' "${!EXP_CODE[@]}" | sort)

# Interactive segment selection if -e was not supplied on the command line
if [[ $EPOCH_SET -eq 0 && -t 0 ]]; then
    echo "Available segments for $PROJECT: ${AVAILABLE_EPOCHS[*]}"
    echo "Select a segment to download:"
    select choice in "${AVAILABLE_EPOCHS[@]}" ALL; do
        if [[ "$choice" == "ALL" || -n "${EXP_CODE[$choice]:-}" ]]; then
            EPOCH="$choice"
            break
        fi
        echo "Invalid choice, try again."
    done
fi

if [[ "$EPOCH" == "ALL" ]]; then
    EPOCHS=("${AVAILABLE_EPOCHS[@]}")
elif [[ -n "${EXP_CODE[$EPOCH]:-}" ]]; then
    EPOCHS=("$EPOCH")
else
    echo "Error: epoch '$EPOCH' not found for project '$PROJECT'." >&2
    echo "Available: ${AVAILABLE_EPOCHS[*]} ALL" >&2
    exit 1
fi

# Interactive data-type selection if no relevant flags were supplied
if [[ $ALL_FITS -eq 0 && $DO_PIPE -eq 0 && $PIPE_ONLY -eq 0 && -t 0 ]]; then
    echo "What would you like to download for segment(s) ${EPOCHS[*]}?"
    echo "  1) First source only (<prefix>_1_1*)"
    echo "  2) All fits files"
    echo "  3) First source only + pipeline data"
    echo "  4) All fits files + pipeline data"
    echo "  5) Pipeline data only"
    read -rp "Enter choice [1-5]: " data_choice
    case "$data_choice" in
        1) ;;
        2) ALL_FITS=1 ;;
        3) DO_PIPE=1 ;;
        4) ALL_FITS=1; DO_PIPE=1 ;;
        5) PIPE_ONLY=1 ;;
        *) echo "Invalid choice." >&2; exit 1 ;;
    esac
fi

# Interactive downloader selection if -d was not supplied on the command line
if [[ $DOWNLOADER_SET -eq 0 && -t 0 ]]; then
    echo "Which download engine would you like to use?"
    select dchoice in wget axel; do
        if [[ "$dchoice" == "wget" || "$dchoice" == "axel" ]]; then
            DOWNLOADER="$dchoice"
            break
        fi
        echo "Invalid choice, try again."
    done
fi

# List filenames in an Apache-style autoindex directory, one per line.
list_remote_files() {
    local url="$1"
    curl -sL "${url}/" \
        | grep -oP '(?<=href=")[^"]+(?=")' \
        | grep -v '^\?' \
        | grep -v '^/'
}

# Run axel, preferring a host install and falling back to the singularity
# container built from vlbi_pipeline/singularity_images/axel_recipe.def.
run_axel() {
    local url="$1" out="$2"
    if command -v axel >/dev/null 2>&1; then
        axel -n "$AXEL_CONNECTIONS" -a -o "$out" "$url"
    else
        # Resolve the physical (symlink-free) cwd and bind it at the same
        # path in the container: apptainer's auto-bind of the underlying
        # filesystem (e.g. /scratch) doesn't cover a symlinked view of it
        # (e.g. ~/scratch -> /scratch/user), which otherwise makes it fail
        # to chdir and silently fall back to $HOME, breaking relative -o paths.
        local real_pwd
        real_pwd="$(pwd -P)"
        if [[ -f "$AXEL_SIF" ]] && command -v apptainer >/dev/null 2>&1; then
            apptainer exec --bind "${real_pwd}:${real_pwd}" --pwd "${real_pwd}" \
                "$AXEL_SIF" axel -n "$AXEL_CONNECTIONS" -a -o "$out" "$url"
        elif [[ -f "$AXEL_SIF" ]] && command -v singularity >/dev/null 2>&1; then
            singularity exec --bind "${real_pwd}:${real_pwd}" --pwd "${real_pwd}" \
                "$AXEL_SIF" axel -n "$AXEL_CONNECTIONS" -a -o "$out" "$url"
        else
            echo "Error: axel not found on host, and no container at $AXEL_SIF" >&2
            echo "Build it with: apptainer build --fakeroot vlbi_pipeline/singularity_images/axel.sif vlbi_pipeline/singularity_images/axel_recipe.def" >&2
            exit 1
        fi
    fi
}

# List a remote directory and axel-download every entry matching a glob
# pattern into dest/.
download_matching_axel() {
    local remote="$1" pattern="$2" dest="$3"
    local fname found=0

    while IFS= read -r fname; do
        [[ -z "$fname" ]] && continue
        case "$fname" in
            $pattern)
                found=1
                if [[ -f "${dest}/${fname}" && ! -f "${dest}/${fname}.st" ]]; then
                    # File exists with no axel state file: a prior run finished
                    # it. Skip without spinning up a container to avoid
                    # re-scanning thousands of already-complete files on every
                    # restart after an interrupted connection.
                    continue
                fi
                echo "  -> $fname"
                run_axel "${remote}/${fname}" "${dest}/${fname}"
                ;;
        esac
    done < <(list_remote_files "$remote")

    if [[ $found -eq 0 ]]; then
        echo "  Warning: no files matching '$pattern' found at $remote" >&2
    fi
}

download_fits() {
    local epoch="$1" exp="$2" prefix="$3"
    local pattern="${prefix}*"
    local dest="${epoch}/data"
    if [[ $ALL_FITS -eq 0 ]]; then
        pattern="${prefix}_1_1*"
        dest="${epoch}/phsref_data"
    fi
    local remote="${BASE_URL}/${exp}/fits"
    mkdir -p "$dest"
    echo "Downloading fits data for segment $epoch (pattern: $pattern) -> $dest [$DOWNLOADER]"
    if [[ "$DOWNLOADER" == "axel" ]]; then
        download_matching_axel "$remote" "$pattern" "$dest"
    else
        wget -t45 -l1 -r -nd -P "$dest" "$remote" -A "$pattern"
    fi
}

download_pipe() {
    local epoch="$1" exp="$2" prefix="$3"
    local dest="${epoch}/evn_pipe"
    local remote="${BASE_URL}/${exp}/pipe"
    mkdir -p "$dest"
    echo "Downloading pipeline data for segment $epoch -> $dest [$DOWNLOADER]"
    if [[ "$DOWNLOADER" == "axel" ]]; then
        download_matching_axel "$remote" "${prefix}*" "$dest"
    else
        wget -t45 -l1 -r -nd -P "$dest" "$remote" -A "${prefix}*"
    fi
}

for epoch in "${EPOCHS[@]}"; do
    exp="${EXP_CODE[$epoch]}"
    prefix="${epoch,,}"

    if [[ $PIPE_ONLY -eq 1 ]]; then
        download_pipe "$epoch" "$exp" "$prefix"
    else
        download_fits "$epoch" "$exp" "$prefix"
        if [[ $DO_PIPE -eq 1 ]]; then
            download_pipe "$epoch" "$exp" "$prefix"
        fi
    fi
done

echo "Done."
