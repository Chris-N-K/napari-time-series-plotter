# napari-time_series_plotter

[![License](https://img.shields.io/pypi/l/napari-time_series_plotter.svg?color=green)](https://github.com/ch-n/napari-time_series_plotter/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-time_series_plotter.svg?color=green)](https://pypi.org/project/napari-time_series_plotter)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-time_series_plotter.svg?color=green)](https://python.org)
[![tests](https://github.com/ch-n/napari-time_series_plotter/workflows/tests/badge.svg)](https://github.com/ch-n/napari-time_series_plotter/actions)
[![codecov](https://codecov.io/gh/ch-n/napari-time_series_plotter/branch/main/graph/badge.svg)](https://codecov.io/gh/ch-n/napari-time_series_plotter)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/napari-time-series-plotter)](https://napari-hub.org/plugins/napari-time-series-plotter)

## Description
Napari-time_series_plotter (TSP) is a plugin for the `napari` image viewer. TSP adds widgets to the viewer to select and visulise pixel / voxel values from one or multiple image layers as line plots. A plot represents the intensity of the selected pixel / voxel over the first dimension (time). TSP supports 3D and 4D images (4D: t+3D, 3D: t+2D).

----------------------------------

## Installation
You can either install the latest version via pip:

    pip install napari-time-series-plotter

or directly in the `napari` viewers plugin manager.

<br>

To install latest development version :

    pip install git+https://github.com/ch-n/napari-time_series_plotter.git

## Usage
<p align="center">
  <img src="https://github.com/ch-n/napari-time_series_plotter/raw/main/napari-time_series_plotter_demo.gif" alt="Demo gif" />
</p>
    
- Select the two TSP widgets LayerSelectror and VoxelPlotter in the `Plugins` tab in the viewer
- Use the LayerSelector to chose the image layers you want to select for plotting
- Move the mouse over the image while holding `Shift`
- The plotter will display graphs for all selected layers and a legend

## ToDo
- [ ] Add Sphinx documentation

## Future goals
- [ ] Add a toolbar for interaction with the figure
- [ ] Add a widget to save the pixel / voxel series to file
- [ ] Combine the standard widgets into one for more convenient usage

## Contributing

Contributions are very welcome. Tests can be run with [tox], please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [BSD-3] license,
"napari-time_series_plotter" is free and open source software

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

--------------

## References
This [napari] plugin was generated with [Cookiecutter] using [@napari]'s [cookiecutter-napari-plugin] template.

Images used in the demo gif were taken from: [The Cancer Imaging Archive] <br>

    DOI: https://doi.org/10.7937/K9/TCIA.2015.VOSN3HN1
    Images: 1.3.6.1.4.1.9328.50.16.281868838636204210586871132130856898223
            1.3.6.1.4.1.9328.50.16.254461916058189583774506642993503110733

[The Cancer Imaging Archive]: https://www.cancerimagingarchive.net/
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
