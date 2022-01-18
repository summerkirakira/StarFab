import time
import typing
import logging
from pathlib import Path
from datetime import datetime
from functools import partial
from collections import namedtuple
from scdatatools.utils import log_time

from starfab.gui import qtc, qtw, qtg
from starfab.log import getLogger
from scdatatools.engine.chunkfile.converter import CGF_CONVERTER_MODEL_EXTS
from starfab.models.common import BackgroundRunnerSignals
from starfab.utils import show_file_in_filemanager

ExtractionItem = namedtuple("ExtractionItem", ["name", "object", "bp_generator"])
logger = getLogger(__name__)


class BlueprintExportLog(qtw.QDialog):
    def __init__(
        self,
        starfab,
        outdir: typing.Union[str, Path],
        items: typing.List[ExtractionItem],
        create_entity_dir: bool = True,
        output_model_log: bool = False,
        export_options: dict = None,
    ):
        super().__init__(parent=starfab)
        self.setMinimumSize(1024, 800)
        self.starfab = starfab
        self.export_options = export_options or {}
        self.create_entity_dir = create_entity_dir
        self.output_model_log = output_model_log

        self.output_tabs = qtw.QTabWidget()
        self.output_tabs.setTabsClosable(False)
        self.setSizeGripEnabled(True)

        self.closebtn = qtw.QDialogButtonBox()
        self.closebtn.setOrientation(qtc.Qt.Horizontal)
        self.closebtn.setStandardButtons(qtw.QDialogButtonBox.Ok)
        self.closebtn.setEnabled(False)
        self.closebtn.clicked.connect(self.close)

        self._last_log_update = time.time()

        layout = qtw.QVBoxLayout()
        layout.addWidget(self.output_tabs)
        layout.addWidget(self.closebtn)
        self.setLayout(layout)

        self.items = items
        self.outdir = Path(outdir)

    def closeEvent(self, event) -> None:
        if self.closebtn.isEnabled():
            event.accept()
        else:
            event.ignore()

    def _output_monitor(
        self,
        msg,
        entity,
        console,
        default_fmt,
        log_file,
        model_log_file,
        overview_console,
        verbose=False,
        progress=None,
        total=None,
        level=logging.INFO,
        exc_info=None,
    ):
        fmt = qtg.QTextCharFormat()
        overview_out = False

        if (time.time() - self._last_log_update) > 0.25:
            qtg.QGuiApplication.processEvents()
            self._last_log_update = time.time()

        if (
            model_log_file
            and msg.startswith("zstd |")
            and any(msg.casefold().endswith(_) for _ in CGF_CONVERTER_MODEL_EXTS)
        ):
            model_log_file.write(f"{msg.split(' | ')[-1]}\n")

        if "WARN" in msg:
            fmt.setFontWeight(qtg.QFont.Bold)
            fmt.setForeground(qtg.QColor("#f5ad42"))
            overview_out = True
        elif "ERROR" in msg:
            fmt.setFontWeight(qtg.QFont.Bold)
            fmt.setForeground(qtg.QColor("#ff4d4d"))
            overview_out = True
        elif not verbose and level <= logging.INFO:
            return
        else:
            fmt = default_fmt
        console.setCurrentCharFormat(fmt)
        console.append(f"{msg}")
        if overview_out:
            overview_console.setCurrentCharFormat(fmt)
            overview_console.append(f"{entity}: {msg}")
        log_file.write(f"{msg}\n")

    def extract_entities(self) -> None:
        overview_tab = qtw.QWidget()
        layout = qtw.QVBoxLayout()
        overview_console = qtw.QTextEdit(overview_tab)
        overview_console.setReadOnly(True)
        default_fmt = overview_console.currentCharFormat()
        layout.addWidget(overview_console)
        overview_tab.setLayout(layout)
        self.output_tabs.addTab(overview_tab, "Overview")
        self.output_tabs.setCurrentWidget(overview_tab)

        overview_console.append("Export Overview")
        overview_console.append("-" * 80)

        start = datetime.now()
        for i, item in enumerate(self.items):
            model_log = ""
            try:
                tab = qtw.QWidget()
                layout = qtw.QVBoxLayout()
                console = qtw.QTextEdit(tab)
                console.setReadOnly(True)
                layout.addWidget(console)
                tab.setLayout(layout)
                self.output_tabs.addTab(tab, item.name)
                self.output_tabs.setCurrentWidget(tab)

                self.setWindowTitle(
                    f"Extracting Entity {i + 1}/{len(self.items)}: {item.name}"
                )
                output_dir = (
                    self.outdir / item.name if self.create_entity_dir else self.outdir
                )
                logfile = (
                    output_dir
                    / f'{item.name}_{datetime.now().strftime("%Y_%m_%d-%H_%M_%S")}.extraction.log'
                )
                logfile.parent.mkdir(parents=True, exist_ok=True)

                if self.output_model_log:
                    model_log = (
                        output_dir
                        / f'{datetime.now().strftime("%Y_%m_%d-%H_%M_%S")}_{item.name}'
                        f".extracted_models.log"
                    ).open("w")

                with logfile.open("w") as log:
                    monitor = partial(
                        self._output_monitor,
                        console=console,
                        entity=item.name,
                        default_fmt=default_fmt,
                        verbose=self.export_options.get("verbose", False),
                        log_file=log,
                        model_log_file=model_log,
                        overview_console=overview_console,
                    )
                    try:
                        with log_time(
                            f"Generating Blueprint for {item.name}",
                            partial(monitor, level=logging.CRITICAL),
                        ):
                            bp = item.bp_generator(
                                self.starfab.sc, item.object, monitor=monitor
                            )
                            bp_file = (output_dir / item.name).with_suffix(".scbp")
                            bp.dump(bp_file.open("w"))
                        with log_time(
                            "Extracting blueprint",
                            partial(monitor, level=logging.CRITICAL),
                        ):
                            bp.extract(outdir=output_dir, **self.export_options)
                    except Exception as e:
                        monitor(f"ERROR: Extraction failed - {e}", level=logging.ERROR)
                        logger.exception(f"Extraction failed")
            except Exception as e:
                print(f"ERROR EXTRACTING SHIP {item}: {e}")
            finally:
                if model_log:
                    model_log.close()

        overview_console.setCurrentCharFormat(default_fmt)
        overview_console.append("-" * 80)
        overview_console.append(
            f"\n\nFinished exporting {len(self.items)} entities in {datetime.now() - start}"
        )
        overview_console.append(f"Output directory: {self.outdir}")
        self.output_tabs.setCurrentWidget(overview_tab)
        show_file_in_filemanager(Path(self.outdir))
        self.closebtn.setEnabled(True)
