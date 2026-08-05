# Generic VLBI pipeline

This is a generic VLBI pipeline for use on clusters (with job managers SLURM & PBS) but can also be used on your home machine. The CASA-based pipeline has been tested on the European VLBI Network (EVN) and Very Long Baseline Array (VLBA) data sets. Only CASA 6.3+ versions are now supported and tested up to CASA version 6.5.4.

As of 03-05-2024, it will only calibrate continuum data sets, but spectral line data sets are planned to be implemented. The pipeline is still under development.

This README includes installation instructions and simple usage, but we suggest you read the [Wiki](.. //wiki) before running or using the pipeline.

## Citing the pipeline

If you use this pipeline, please make sure that you cite this repository using the bibtex or zenodo code below

```
Jack Radcliffe, (2024). jradcliffe5/VLBI_pipeline: v1.1 (v1.1). Zenodo. https://doi.org/10.5281/zenodo.11108171``
```
```
@software{jack_radcliffe_2024_11108171,
  author       = {Jack Radcliffe},
  title        = {jradcliffe5/VLBI\_pipeline: v1.1},
  month        = may,
  year         = 2024,
  publisher    = {Zenodo},
  version      = {v1.1},
  doi          = {10.5281/zenodo.11108171},
  url          = {https://doi.org/10.5281/zenodo.11108171}
}
```

## Installation Instructions
### For self-contained CASA
1. Install CASA from <https://casa.nrao.edu> and ensure that it is v6.3+. Any earlier versions do not include the fringe-fitting capabilities.
2. Clone this repository in any directory desired. 

### For modular CASA
1. Install CASA following the instructions in <https://casadocs.readthedocs.io/en/stable/notebooks/introduction.html#Modular-Packages>
2. Install astropy and/or pyfits using `pip install pyfits astropy`
3. Clone this repository in any directory required.

## Usage Instructions
Before starting to use the pipeline, it is highly advised that you check the wiki which will give you all the information regarding the parameters that need to be set or can be changed. The pipeline is designed to be highly customisable so the inputs lists are fairly long. 

1. Copy the `vlbi_pipe_inputs.txt` and `vlbi_pipe_params.json` files to the directory where you want to reduce the data (you can pick any directory but this allows for easy bookkeeping)
2. Edit `vlbi_pipe_inputs.txt` to include the location of the `vlbi_pipe_params.json` and edit the steps of what you'd like to be run (1=run, 0=don't run)
3. Edit `vlbi_pipe_params.json` to tailor the calibration steps. Most importantly, set the global params (see the wiki for details)

### Generating the parset automatically
Rather than filling in the global parameters by hand, `generate_parset.py` can derive them from the FITS-IDI files and/or the vex schedule:

```
python generate_parset.py -i <directory with the FITS-IDI files> --cwd <directory to reduce the data in>
```

It reads the project code, array, correlator, frequency setup and the full scan list, then works out the reference antenna order (by sensitivity) and which sources are fringe finders, phase calibrators (including check sources) and targets from the structure of the schedule. Phase calibrators serving the same field are written out furthest from the target first, so that a chain of phase reference sources is calibrated inwards towards the science field. Independent target/phase calibrator pairs are instead put in a single `phase_referencing/select_calibrators` pass, since every caltable is applied to every target with `gainfield=''` - one pass per pair would transfer each pair's solutions onto all the other targets. Everything it cannot infer (HPC settings, CASA paths, solution intervals) is inherited from a template parset, by default the `vlbi_pipe_params.json` in the repository, so the result is always complete. It only needs astropy, not CASA.

Useful options: `-v <vexfile>` to add/force a schedule (auto-detected next to the data otherwise), `--dry-run` to print instead of write, `-t` for a different template, and `--targets`/`--phase-calibrators`/`--fringe-finders` to override the classification. Always check the source classification table it prints before running the pipeline.

#### Sizing the solution intervals from the data (`--estimate-snr`)
With `--estimate-snr` it reads one scan of each calibrator and runs a coarse delay/rate FFT per baseline, which gives the SNR a fringe fit would reach without needing a flux scale or Tsys - correlator amplitudes are already normalised correlation coefficients, so `SNR = rho*sqrt(2*bandwidth*time)`.

```
CALIBRATOR             TIME USED SNR/BASELINE    SNR/ANTENNA    WEAKEST
J0530+1331              4.0 min        382.2          734.1         NT
J1031+7441              1.6 min         28.9           45.9         NT
```

The per-antenna value (every baseline to that antenna combined, as a fringe fit does) is scaled by `sqrt(interval)` and by `sqrt(nspw)` if the spws are combined, and any solution interval in the template that cannot reach `1.5 x min_snr` is lengthened until it can. Intervals the calibrators already support are left untouched, `inf` is never shortened, and if a pass only works with the spws combined then `combine` is set to `spw` for it. A calibrator too weak even for a whole scan with every spw combined is reported as needing in-beam calibration or the `mssc` step. Costs a few seconds per FITS-IDI file.

By default only the single longest scan of each calibrator is measured. Add `--average-scans` (implies `--estimate-snr`) to measure every scan instead and combine their per-baseline SNRs in quadrature - slower, but the result no longer depends on whichever one scan happened to be picked, so an antenna that was off source (parked, slewing, flagged) for just that scan doesn't drop out of the measurement entirely.

Adding `--tune-cal-types` (which implies `--estimate-snr`) also drops self-calibration steps the calibrators cannot solve, holding amplitude steps to twice the SNR of a phase-only solve. Dropped steps are removed from `cal_type`, `sol_interval`, `combine` and `interp_flagged` together so the lists stay aligned, and at least one step is always kept.

#### Frequency-dependent settings
These are applied whether or not the SNR is measured, from the reference frequency in the data:

* `ionex_options/run` is switched on below 8 GHz and off above, where the ionosphere stops mattering.
* `do_disp_delays` is switched on below 5 GHz for `sub_band_delay`. For `phase_referencing` it additionally requires the weakest calibrator to have SNR to spare, since a dispersive term is another free parameter.
* Any solve carrying phase (`f`, `p`, `ap`, `k`) is capped at a rule-of-thumb tropospheric coherence time of roughly `1000/nu_GHz` seconds - about 10 min at L band, 2 min at X band and 20 s at Q band. Averaging phase past this gains nothing, so when a calibrator is too weak the spws are combined rather than the interval stretched further. Pure amplitude solves are not capped.

### For CASA 5
4. Run CASA to generate the bash scripts that will run the pipeline using `casa -c <path to VLBI pipeline repo>/run_vlbi_pipe.py <path to input file>/vlbi_pipe_inputs.txt`
5. This will generate a bash script in the cwd called `vp_runfile.bash`. Execute and start the pipeline with `bash vp_runfile.bash`

### For CASA 6
4. Run CASA to generate the bash scripts that will run the pipeline using `python <path to VLBI pipeline repo>/run_vlbi_pipe.py <path to input file>/vlbi_pipe_inputs.txt`
5. This will generate a bash script in the cwd called `vp_runfile.bash`. Execute and start the pipeline with `bash vp_runfile.bash`


