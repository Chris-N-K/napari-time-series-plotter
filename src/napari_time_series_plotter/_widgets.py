from qtpy.QtWidgets import QCheckBox


class TSPCheckBox(QCheckBox):
    """CheckBox widget class derived from qtpy.QtWidgets.QCheckBox

    Adds the attribute layer and the event connectable method rename to the original class.
    """
    def __init__(self, layer):
        """Instance initialisation.

        :param layer: Connected napari viewer layer
        :type layer: napari.layers.Image
        """
        super().__init__()
        self.layer = layer
        self.setText(layer.name)

    def rename(self, event):
        """Rename check box upon layer name change.

        Sets the instance attribute `text` to self.layer.name. Should be connected to the layers `name` event.
        """
        self.setText(self.layer.name)
