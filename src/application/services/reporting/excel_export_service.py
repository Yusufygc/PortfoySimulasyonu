# src/application/services/excel_export_service.py

import logging
from datetime import date
from pathlib import Path
from typing import Union

from src.application.services.reporting.daily_history_models import ExportMode
from src.application.services.simulation.history_simulation_service import HistorySimulationService
from src.application.services.reporting.excel_report_builder import ExcelReportBuilder

logger = logging.getLogger(__name__)

class ExcelExportService:
    """
    Facade class that coordinates history simulation and excel reporting.
    This preserves the interface for the UI, while delegating the heavy lifting
    to HistorySimulationService and ExcelReportBuilder (SRP Fix).
    """
    def __init__(
        self,
        simulation_service: HistorySimulationService,
        report_builder: ExcelReportBuilder,
    ) -> None:
        self.simulation_service = simulation_service
        self.report_builder = report_builder

    def export_history(
        self,
        start_date: date,
        end_date: date,
        file_path: Union[str, Path],
        mode: ExportMode = ExportMode.OVERWRITE,
    ) -> None:
        file_path = Path(file_path)
        
        # 1. Simulate the history
        daily_positions, daily_snapshots = self.simulation_service.simulate_history(
            start_date=start_date, 
            end_date=end_date
        )
        
        # 2. Build pandas dataframes and write to excel with formatting
        self.report_builder.build_and_save(
            file_path=file_path, 
            daily_positions=daily_positions,
            daily_snapshots=daily_snapshots,
            mode=mode
        )
