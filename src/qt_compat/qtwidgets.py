"""QtWidgets compatibility exports for PySide6."""

from PySide6.QtWidgets import *  # noqa: F403
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QSizePolicy,
    QToolButton,
)


def _alias(cls, name: str, value) -> None:
    if not hasattr(cls, name):
        setattr(cls, name, value)


_alias(QHeaderView, "Stretch", QHeaderView.ResizeMode.Stretch)
_alias(QHeaderView, "Fixed", QHeaderView.ResizeMode.Fixed)
_alias(QHeaderView, "ResizeToContents", QHeaderView.ResizeMode.ResizeToContents)

_alias(QSizePolicy, "Fixed", QSizePolicy.Policy.Fixed)
_alias(QSizePolicy, "Minimum", QSizePolicy.Policy.Minimum)
_alias(QSizePolicy, "Maximum", QSizePolicy.Policy.Maximum)
_alias(QSizePolicy, "Preferred", QSizePolicy.Policy.Preferred)
_alias(QSizePolicy, "Expanding", QSizePolicy.Policy.Expanding)
_alias(QSizePolicy, "Ignored", QSizePolicy.Policy.Ignored)

_alias(QFrame, "NoFrame", QFrame.Shape.NoFrame)
_alias(QFrame, "HLine", QFrame.Shape.HLine)
_alias(QFrame, "VLine", QFrame.Shape.VLine)
_alias(QFrame, "StyledPanel", QFrame.Shape.StyledPanel)

_alias(QAbstractItemView, "SelectRows", QAbstractItemView.SelectionBehavior.SelectRows)
_alias(QAbstractItemView, "SingleSelection", QAbstractItemView.SelectionMode.SingleSelection)

_alias(QToolButton, "InstantPopup", QToolButton.ToolButtonPopupMode.InstantPopup)
_alias(QLineEdit, "LeadingPosition", QLineEdit.ActionPosition.LeadingPosition)

_alias(QDialog, "Accepted", QDialog.DialogCode.Accepted)
_alias(QDialog, "Rejected", QDialog.DialogCode.Rejected)

_alias(QMessageBox, "Yes", QMessageBox.StandardButton.Yes)
_alias(QMessageBox, "No", QMessageBox.StandardButton.No)
_alias(QMessageBox, "Ok", QMessageBox.StandardButton.Ok)
_alias(QMessageBox, "Question", QMessageBox.Icon.Question)
_alias(QMessageBox, "YesRole", QMessageBox.ButtonRole.YesRole)
_alias(QMessageBox, "NoRole", QMessageBox.ButtonRole.NoRole)
