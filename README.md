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

### For CASA 5
4. Run CASA to generate the bash scripts that will run the pipeline using `casa -c <path to VLBI pipeline repo>/run_vlbi_pipe.py <path to input file>/vlbi_pipe_inputs.txt`
5. This will generate a bash script in the cwd called `vp_runfile.bash`. Execute and start the pipeline with `bash vp_runfile.bash`

### For CASA 6
4. Run CASA to generate the bash scripts that will run the pipeline using `python <path to VLBI pipeline repo>/run_vlbi_pipe.py <path to input file>/vlbi_pipe_inputs.txt`
5. This will generate a bash script in the cwd called `vp_runfile.bash`. Execute and start the pipeline with `bash vp_runfile.bash`


