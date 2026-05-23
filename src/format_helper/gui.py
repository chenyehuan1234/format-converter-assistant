from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import __app_name__, __version__
from .config import AppSettings, SettingsStore, WINDOW_TITLE, logs_dir
from .dependencies import DependencyManager
from .engines import EngineRegistry
from .files import default_output_path, scan_inputs
from .history import HistoryStore
from .job_queue import JobQueue
from .models import ConversionJob, ConversionPreset, JobStatus, detect_kind
from .updater import GitHubUpdater


LIGHT_STYLE = """
QMainWindow, QWidget { background: #f7f8fa; color: #202124; font-size: 13px; }
QPushButton { background: #2563eb; color: white; border: 0; padding: 8px 12px; border-radius: 6px; }
QPushButton:disabled { background: #94a3b8; }
QTableWidget, QTextEdit, QLineEdit, QComboBox, QSpinBox { background: white; border: 1px solid #d6dae1; border-radius: 6px; padding: 4px; }
"""

DARK_STYLE = """
QMainWindow, QWidget { background: #181b20; color: #edf2f7; font-size: 13px; }
QPushButton { background: #3b82f6; color: white; border: 0; padding: 8px 12px; border-radius: 6px; }
QPushButton:disabled { background: #475569; }
QTableWidget, QTextEdit, QLineEdit, QComboBox, QSpinBox { background: #222832; color: #edf2f7; border: 1px solid #3d4654; border-radius: 6px; padding: 4px; }
"""


class DropZone(QLabel):
    filesDropped = Signal(list)

    def __init__(self) -> None:
        super().__init__("拖拽文件或文件夹到这里\n支持图片、音频、视频、Office 文档和 PDF")
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(150)
        self.setStyleSheet("border: 2px dashed #7c8aa5; border-radius: 8px; font-size: 17px;")

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls()]
        self.filesDropped.emit(paths)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()
        self.history = HistoryStore()
        self.dependencies = DependencyManager()
        self.queue = JobQueue(EngineRegistry(), self.history, self.settings.max_workers)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(500)
        self.refresh_timer.timeout.connect(self._refresh_table)
        self.setWindowTitle(f"{WINDOW_TITLE} {__version__}")
        self.resize(1120, 740)
        self._build_ui()
        self._apply_theme()
        self._refresh_dependencies()
        self._first_run_check()

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self._conversion_tab(), "转换")
        tabs.addTab(self._history_tab(), "历史")
        tabs.addTab(self._settings_tab(), "设置")
        self.setCentralWidget(tabs)

        check_action = QAction("检查更新", self)
        check_action.triggered.connect(self._check_update)
        self.menuBar().addAction(check_action)

    def _conversion_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.drop_zone = DropZone()
        self.drop_zone.filesDropped.connect(self._add_paths)
        layout.addWidget(self.drop_zone)

        controls = QHBoxLayout()
        add_button = QPushButton("选择文件")
        add_button.clicked.connect(self._choose_files)
        folder_button = QPushButton("选择文件夹")
        folder_button.clicked.connect(self._choose_folder)
        self.target_combo = QComboBox()
        self.target_combo.addItems(["pdf", "txt", "png", "jpg", "webp", "mp3", "wav", "flac", "mp4", "mkv"])
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["balanced", "high", "small"])
        self.output_dir = QLineEdit(self.settings.output_dir)
        self.output_dir.setPlaceholderText("留空则保存到源文件旁 converted 文件夹")
        output_button = QPushButton("输出目录")
        output_button.clicked.connect(self._choose_output)
        controls.addWidget(add_button)
        controls.addWidget(folder_button)
        controls.addWidget(QLabel("目标格式"))
        controls.addWidget(self.target_combo)
        controls.addWidget(QLabel("预设"))
        controls.addWidget(self.quality_combo)
        controls.addWidget(self.output_dir, 1)
        controls.addWidget(output_button)
        layout.addLayout(controls)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["文件", "类型", "输出", "状态", "进度", "错误"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        run_button = QPushButton("开始转换")
        run_button.clicked.connect(self._run_jobs)
        cancel_button = QPushButton("取消等待任务")
        cancel_button.clicked.connect(self._cancel_pending)
        clear_button = QPushButton("清除已完成")
        clear_button.clicked.connect(self._clear_completed)
        open_logs = QPushButton("打开日志目录")
        open_logs.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(logs_dir()))))
        actions.addWidget(run_button)
        actions.addWidget(cancel_button)
        actions.addWidget(clear_button)
        actions.addStretch(1)
        actions.addWidget(open_logs)
        layout.addLayout(actions)
        return page

    def _history_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        refresh = QPushButton("刷新历史")
        refresh.clicked.connect(self._refresh_history)
        clear = QPushButton("清空历史")
        clear.clicked.connect(self._clear_history)
        row = QHBoxLayout()
        row.addWidget(refresh)
        row.addWidget(clear)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(self.history_text)
        self._refresh_history()
        return page

    def _settings_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        self.theme_combo.setCurrentText(self.settings.theme)
        self.theme_combo.currentTextChanged.connect(self._save_settings)
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, max(1, (os.cpu_count() or 2)))
        self.workers_spin.setValue(self.settings.max_workers)
        self.workers_spin.valueChanged.connect(self._save_settings)
        self.owner_input = QLineEdit(self.settings.github_owner)
        self.repo_input = QLineEdit(self.settings.github_repo)
        self.auto_update_check = QCheckBox("启动时自动检查更新")
        self.auto_update_check.setChecked(self.settings.auto_update)
        for widget in (self.owner_input, self.repo_input):
            widget.textChanged.connect(self._save_settings)
        self.auto_update_check.stateChanged.connect(self._save_settings)
        form.addRow("主题", self.theme_combo)
        form.addRow("并发数", self.workers_spin)
        form.addRow("GitHub Owner", self.owner_input)
        form.addRow("GitHub Repo", self.repo_input)
        form.addRow("自动更新", self.auto_update_check)
        layout.addLayout(form)

        deps_row = QHBoxLayout()
        refresh_deps = QPushButton("刷新依赖")
        refresh_deps.clicked.connect(self._refresh_dependencies)
        prepare_deps = QPushButton("一键准备依赖")
        prepare_deps.clicked.connect(self._prepare_dependencies)
        deps_row.addWidget(refresh_deps)
        deps_row.addWidget(prepare_deps)
        deps_row.addStretch(1)
        layout.addLayout(deps_row)
        self.deps_text = QTextEdit()
        self.deps_text.setReadOnly(True)
        layout.addWidget(self.deps_text, 1)
        return page

    def _add_paths(self, paths: list[Path]) -> None:
        files = scan_inputs(paths, recursive=True)
        if not files:
            QMessageBox.information(self, __app_name__, "没有找到支持的文件。")
            return
        target = self.target_combo.currentText()
        output_root = Path(self.output_dir.text()) if self.output_dir.text().strip() else None
        for path in files:
            preset = ConversionPreset(target_format=target, quality=self.quality_combo.currentText())
            job = ConversionJob(
                input_path=path,
                preset=preset,
                output_path=default_output_path(path, target, output_root),
            )
            job.kind = detect_kind(path, target)
            self.queue.add(job)
        self._refresh_table()

    def _choose_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件")
        if files:
            self._add_paths([Path(file) for file in files])

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self._add_paths([Path(folder)])

    def _choose_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if folder:
            self.output_dir.setText(folder)
            self._save_settings()

    def _run_jobs(self) -> None:
        self.queue.max_workers = self.workers_spin.value()
        self.queue.run_all()
        self.refresh_timer.start()
        self._refresh_table()

    def _cancel_pending(self) -> None:
        self.queue.cancel_pending()
        self._refresh_table()

    def _clear_completed(self) -> None:
        self.queue.clear_completed()
        self._refresh_table()

    def _refresh_table(self) -> None:
        self.table.setRowCount(len(self.queue.jobs))
        for row, job in enumerate(self.queue.jobs):
            values = [
                str(job.input_path),
                job.kind.value,
                str(job.output_path),
                job.status.value,
                str(job.progress),
                job.error,
            ]
            for col, value in enumerate(values):
                if col == 4:
                    bar = QProgressBar()
                    bar.setValue(job.progress)
                    self.table.setCellWidget(row, col, bar)
                else:
                    self.table.setItem(row, col, QTableWidgetItem(value))
        if self.refresh_timer.isActive() and not any(
            job.status == JobStatus.RUNNING for job in self.queue.jobs
        ):
            self.refresh_timer.stop()

    def _refresh_history(self) -> None:
        rows = self.history.recent()
        if not rows:
            self.history_text.setPlainText("暂无历史记录。")
            return
        text = "\n\n".join(
            f"{row['status']} | {row['input_path']} -> {row['output_path']}\n{row['error']}"
            for row in rows
        )
        self.history_text.setPlainText(text)

    def _clear_history(self) -> None:
        self.history.clear()
        self._refresh_history()

    def _refresh_dependencies(self) -> None:
        if not hasattr(self, "deps_text"):
            return
        lines = []
        for status in self.dependencies.all_statuses():
            marker = "可用" if status.available else "缺失"
            detail = f" ({status.path})" if status.path else ""
            lines.append(f"{status.name}: {marker} - {status.detail}{detail}")
        self.deps_text.setPlainText("\n".join(lines))

    def _prepare_dependencies(self) -> None:
        QMessageBox.information(self, "依赖准备", "\n".join(self.dependencies.prepare_missing()))

    def _first_run_check(self) -> None:
        missing = [status for status in self.dependencies.all_statuses() if not status.available]
        if missing:
            QTimer.singleShot(
                500,
                lambda: QMessageBox.information(
                    self,
                    "首次运行向导",
                    "检测到部分转换引擎缺失，请到“设置”页查看依赖状态。\n\n"
                    + "\n".join(f"- {item.name}: {item.detail}" for item in missing),
                ),
            )
        if self.settings.auto_update:
            QTimer.singleShot(1000, self._check_update_silent)

    def _check_update_silent(self) -> None:
        try:
            info = GitHubUpdater(self.settings.github_owner, self.settings.github_repo).check()
            if info.available:
                self._show_update(info)
        except Exception:
            pass

    def _check_update(self) -> None:
        try:
            info = GitHubUpdater(self.settings.github_owner, self.settings.github_repo).check()
            if info.available:
                self._show_update(info)
            else:
                QMessageBox.information(self, "检查更新", info.message)
        except Exception as exc:
            QMessageBox.warning(self, "检查更新失败", str(exc))

    def _show_update(self, info) -> None:
        choice = QMessageBox.question(
            self,
            "发现新版本",
            f"当前版本 {info.current_version}，最新版本 {info.latest_version}。\n是否下载并自动安装？",
        )
        if choice == QMessageBox.Yes:
            try:
                GitHubUpdater(self.settings.github_owner, self.settings.github_repo).download_and_install(info)
            except Exception as exc:
                QMessageBox.warning(self, "自动更新失败", str(exc))

    def _save_settings(self) -> None:
        self.settings = AppSettings(
            theme=self.theme_combo.currentText() if hasattr(self, "theme_combo") else self.settings.theme,
            max_workers=self.workers_spin.value() if hasattr(self, "workers_spin") else self.settings.max_workers,
            output_dir=self.output_dir.text() if hasattr(self, "output_dir") else self.settings.output_dir,
            github_owner=self.owner_input.text() if hasattr(self, "owner_input") else self.settings.github_owner,
            github_repo=self.repo_input.text() if hasattr(self, "repo_input") else self.settings.github_repo,
            auto_update=(
                self.auto_update_check.isChecked()
                if hasattr(self, "auto_update_check")
                else self.settings.auto_update
            ),
        )
        self.settings_store.save(self.settings)
        self.queue.max_workers = self.settings.max_workers
        self._apply_theme()

    def _apply_theme(self) -> None:
        QApplication.instance().setStyleSheet(DARK_STYLE if self.settings.theme == "dark" else LIGHT_STYLE)


def run() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
