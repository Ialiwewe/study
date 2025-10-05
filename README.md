# Well Log Plotter

This repository contains a small Python utility that converts an Excel workbook
containing wireline log data into a composite well-log plot similar to the
reference image.  The layout of the log (tracks, curves, limits, etc.) is
driven by a JSON configuration file so that you can adapt it to a different
well without modifying the code.

## Requirements

The script depends on the following Python packages:

- [pandas](https://pandas.pydata.org/) for reading Excel workbooks.
- [matplotlib](https://matplotlib.org/) for plotting.
- [openpyxl](https://openpyxl.readthedocs.io/) (installed automatically with
  pandas in most environments) to read `.xlsx` files.

Create and activate a virtual environment, then install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install pandas matplotlib openpyxl
```

## Usage

```bash
python plot_well_log.py path/to/your_log.xlsx --output my_well.png
```

Key options:

- `--sheet`: Name or index of the worksheet to load if your Excel file
  contains multiple sheets.
- `--config`: Path to a JSON file describing the tracks and curves to plot.
  If omitted, the script uses `configs/default_well_log.json` which mirrors the
  layout shown in the example image.
- `--depth-column`: Override the depth column specified in the configuration if
  your workbook uses a different header (e.g. `DEPTH` instead of `Depth_ft`).
- `--title`: Custom figure title.
- `--output`: Destination file (supports PNG, PDF, SVG, etc.).

The default configuration expects the following columns to be present in the
Excel sheet:

| Column name                | Description                          |
|----------------------------|--------------------------------------|
| `Depth_ft`                 | Depth measured in feet               |
| `SponPotential_mv`         | Spontaneous potential (mV)            |
| `GammaRay_api`             | Gamma-ray log (API units)            |
| `Resistivity_Shallow_ohmm` | Shallow resistivity (ohm·m)          |
| `Resistivity_Medium_ohmm`  | Medium resistivity (ohm·m)           |
| `Resistivity_Deep_ohmm`    | Deep resistivity (ohm·m)             |
| `Density_gcc`              | Bulk density (g/cc)                  |
| `NeutronPorosity_vv`       | Neutron porosity (v/v)               |
| `Porosity_core_vv`         | Core porosity (v/v)                  |
| `WaterSaturation_frac`     | Water saturation (fraction)          |

If your Excel file uses different headers, copy the default configuration file
and update the `column` names inside each track to match your dataset.

```bash
cp configs/default_well_log.json my_config.json
# Edit my_config.json with your preferred curve names and axis limits
python plot_well_log.py my_well.xlsx --config my_config.json
```

The configuration supports additional options such as logarithmic axes,
shading between curves (used for the density/neutron track), and reference
lines.  Comments inside `plot_well_log.py` describe the supported keys.

## Output

The script writes a high-resolution PNG (`well_log.png` by default) to the
current directory.  You can change the output format and file name with the
`--output` option.  The depth axis is shared across tracks and inverted so that
increasing depth plots downward, consistent with typical well-log displays.
