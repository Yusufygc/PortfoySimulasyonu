"""ListTableModel — genel amaçlı QAbstractTableModel taban sınıfı testleri (bkz. plan §7.1 d1)."""
from __future__ import annotations

from src.qt_compat.qtcore import QModelIndex, Qt
from src.ui_qml.models.base_table_model import ColumnSpec, ListTableModel

_COLUMNS = (
    ColumnSpec("Ad", lambda row: row["name"]),
    ColumnSpec("Değer", lambda row: row["value"]),
)


def _model(rows=()):
    return ListTableModel(columns=_COLUMNS, rows=rows)


class TestDimensions:
    def test_row_count_matches_rows(self, qapp):
        model = _model([{"name": "A", "value": 1}, {"name": "B", "value": 2}])
        assert model.rowCount() == 2

    def test_column_count_matches_column_specs(self, qapp):
        model = _model()
        assert model.columnCount() == 2

    def test_row_count_is_zero_for_valid_parent(self, qapp):
        model = _model([{"name": "A", "value": 1}])
        assert model.rowCount(model.index(0, 0)) == 0


class TestData:
    def test_display_role_returns_accessor_value(self, qapp):
        model = _model([{"name": "A", "value": 1}, {"name": "B", "value": 2}])
        assert model.data(model.index(1, 0), Qt.DisplayRole) == "B"
        assert model.data(model.index(1, 1), Qt.DisplayRole) == 2

    def test_invalid_index_returns_none(self, qapp):
        model = _model([{"name": "A", "value": 1}])
        assert model.data(QModelIndex(), Qt.DisplayRole) is None

    def test_unsupported_role_returns_none(self, qapp):
        model = _model([{"name": "A", "value": 1}])
        assert model.data(model.index(0, 0), Qt.DecorationRole) is None


class TestHeaderData:
    def test_horizontal_header_returns_column_titles(self, qapp):
        model = _model()
        assert model.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "Ad"
        assert model.headerData(1, Qt.Horizontal, Qt.DisplayRole) == "Değer"

    def test_vertical_header_returns_none(self, qapp):
        model = _model()
        assert model.headerData(0, Qt.Vertical, Qt.DisplayRole) is None


class TestSetRows:
    def test_set_rows_replaces_data_and_row_count(self, qapp):
        model = _model([{"name": "A", "value": 1}])
        model.set_rows([{"name": "X", "value": 9}, {"name": "Y", "value": 8}])

        assert model.rowCount() == 2
        assert model.data(model.index(0, 0), Qt.DisplayRole) == "X"

    def test_row_at_returns_underlying_row_object(self, qapp):
        row = {"name": "A", "value": 1}
        model = _model([row])
        assert model.row_at(0) is row
