# napari-time_series_plotter

[![License](https://img.shields.io/pypi/l/napari-time_series_plotter.svg?color=green)](https://github.com/ch-n/napari-time_series_plotter/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-time_series_plotter.svg?color=green)](https://pypi.org/project/napari-time_series_plotter)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-time_series_plotter.svg?color=green)](https://python.org)
[![tests](https://github.com/ch-n/napari-time_series_plotter/workflows/tests/badge.svg)](https://github.com/ch-n/napari-time_series_plotter/actions)
[![codecov](https://codecov.io/gh/ch-n/napari-time_series_plotter/branch/main/graph/badge.svg)](https://codecov.io/gh/ch-n/napari-time_series_plotter)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/napari-time-series-plotter)](https://napari-hub.org/plugins/napari-time-series-plotter)

A Plugin for napari to visualize pixel / voxel values over the first dimension (time -> t+3D, t+2D) as graphs.

----------------------------------

This [napari] plugin was generated with [Cookiecutter] using [@napari]'s [cookiecutter-napari-plugin] template.

<!--
Don't miss the full getting started guide to set up your new package:
https://github.com/napari/cookiecutter-napari-plugin#getting-started

and review the napari docs for plugin developers:
https://napari.org/docs/plugins/index.html
-->

## Installation
You can install `napari-time_series_plotter` via [pip]:

    pip install napari-time-series-plotter



To install latest development version :

    pip install git+https://github.com/ch-n/napari-time_series_plotter.git

## Usage
After installation the plugin adds two widgets to the viewer, one is for selecting the layers you want to examine and the other contains the plot.

If you selected at least one layer, moving your mouse over the image while holing shift will display the time series data of the hovered voxel as a graph in the plot widget. In the upper right corner a legend with the layer names will be displayed.

![Usage Gif](https://github.com/ch-n/napari-time_series_plotter/raw/main/Usage.gif)

Only 3D and 4D images are supported. Selecting a layer of different dimensionality will result in a waring without plotting anything.

## ToDo
- [X] Add simple usage instructions to README
- [X] Add gif highlighting usage to README
- [X] Complete unit tests
- [X] Complete in code documentation
- [ ] Add Sphinx documentation
- [ ] Upload to PyPi

## Contributing

Contributions are very welcome. Tests can be run with [tox], please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [BSD-3] license,
"napari-time_series_plotter" is free and open source software

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

[napari]: https://github.com/napari/napari
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[@napari]: https://github.com/napari
[MIT]: http://opensource.org/licenses/MIT
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[GNU GPL v3.0]: http://www.gnu.org/licenses/gpl-3.0.txt
[GNU LGPL v3.0]: http://www.gnu.org/licenses/lgpl-3.0.txt
[Apache Software License 2.0]: http://www.apache.org/licenses/LICENSE-2.0
[Mozilla Public License 2.0]: https://www.mozilla.org/media/MPL/2.0/index.txt
[cookiecutter-napari-plugin]: https://github.com/napari/cookiecutter-napari-plugin

[file an issue]: https://github.com/ch-n/napari-time_series_plotter/issues

[napari]: https://github.com/napari/napari
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
