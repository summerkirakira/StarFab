import typing

from scdatatools.utils import parse_bool

from starfab.gui import qtc, qtw, qtg
from starfab.resources import RES_PATH
from starfab.gui.widgets.dock_widgets.common import StarFabStaticWidget

EXPORT_SETTINGS = {
    # {scdatatools reference}: [ {widget_name}, {settings_key} ]
    "cryxml_fmt": ['opt_cryxmlFmt', 'convert/cryxml_fmt'],
    "img_fmt": ['opt_imgFmt', 'convert/img_fmt'],
    "extract_model_assets": ['opt_extractModelAssets', 'extract/extract_model_assets'],
    "auto_unsplit_textures": ['opt_autoUnsplitTextures', "extract/auto_unsplit_textures"],
    "auto_convert_textures": ['opt_autoConvertTextures', "extract/auto_convert_textures"],
    "auto_convert_sounds": ['opt_autoConvertSounds', "extract/auto_convert_sounds"],
    "auto_convert_models": ['opt_convertModelsDAE', "extract/auto_convert_models"],
    "create_sub_folder": ['opt_createSubFolder', "extract/create_sub_folder"],
    "gen_model_log": ['opt_genModelLog', "extract/gen_model_log"],
    "overwrite": ['opt_overwriteExisting', "extract/overwrite_existing"],
    "auto_open_folder": ['opt_autoOpenExportFolder', "extract/auto_open_folder"],
    "verbose": ['opt_verbose', "extract/verbose"],
}


class ExportOptionsWidget(StarFabStaticWidget):
    __ui_file__ = str(RES_PATH / "ui" / "ExportSettingsForm.ui")

    def __init__(self, exclude: typing.List[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = []
        exclude = exclude or []
        for k, v in EXPORT_SETTINGS.items():
            if (w := getattr(self, v[0], None)) is not None:
                if k in exclude:
                    w.setVisible(False)
                    continue
                if isinstance(w, qtw.QCheckBox):
                    w.stateChanged.connect(self.save_settings)
                elif isinstance(w, qtw.QComboBox):
                    w.activated.connect(self.save_settings)
                else:
                    continue
                self.options.append(k)
        self._resetting = False
        self.reset_from_settings()

    def reset_from_settings(self):
        self._resetting = True
        try:
            for option in self.options:
                w = getattr(self, EXPORT_SETTINGS[option][0])
                if isinstance(w, qtw.QCheckBox):
                    w.setChecked(parse_bool(self.starfab.settings.value(EXPORT_SETTINGS[option][1])))
                elif isinstance(w, qtw.QComboBox):
                    w.setCurrentText(str(self.starfab.settings.value(EXPORT_SETTINGS[option][1])).lower())
        finally:
            self._resetting = False

    def save_settings(self):
        if self._resetting:
            return
        for option in self.options:
            w = getattr(self, EXPORT_SETTINGS[option][0])
            if isinstance(w, qtw.QCheckBox):
                self.starfab.settings.setValue(EXPORT_SETTINGS[option][1], w.isChecked())
            elif isinstance(w, qtw.QComboBox):
                self.starfab.settings.setValue(EXPORT_SETTINGS[option][1], w.currentText())
        self.on_opt_autoConvertTextures_stateChanged()

    def get_options(self):
        opts = {'converters': []}
        for option in self.options:
            w = getattr(self, EXPORT_SETTINGS[option][0])
            if isinstance(w, qtw.QCheckBox):
                opts[option] = w.isChecked()
            elif isinstance(w, qtw.QComboBox):
                opts[option] = w.currentText()

        if opts.get('extract_model_assets', False):
            opts["converters"].append("model_assets_extractor")
        if opts.get('cryxml_fmt').lower() != "cryxmlb":
            opts["converters"].append("cryxml_converter")
        if opts.get('auto_unsplit_textures', False):
            opts["converters"].append("ddstexture_converter")
            if opts.get('auto_convert_textures', False):
                opts["convert_dds_fmt"] = opts.get('img_fmt', self.starfab.settings.value('convert/img_fmt'))
            else:
                opts["convert_dds_fmt"] = "dds"
        if opts.get('auto_convert_models', False):
            opts["converters"].append("cgf_converter")

        return opts

    @qtc.Slot()
    def on_opt_autoConvertTextures_stateChanged(self):
        # this is auto-connected from the .ui
        if self.opt_autoConvertTextures.isChecked():
            self.opt_autoUnsplitTextures.setChecked(True)
            self.opt_autoUnsplitTextures.setEnabled(False)
        else:
            self.opt_autoUnsplitTextures.setEnabled(True)
