"""
對話框套件
"""

from dialogs.qr_dialog import QRCodeDialog
from dialogs.version_dialog import VersionSelectionDialog
from dialogs.migration_dialog import MigrationReportDialog
from dialogs.bordered_dialog import BorderedDialog

__all__ = [
    "QRCodeDialog",
    "VersionSelectionDialog",
    "MigrationReportDialog",
    "BorderedDialog",
]
