from __future__ import annotations
from src.domain.models.risk_profile import RiskLabel

def display_ticker(ticker: str | None) -> str:
    """Return a UI-facing ticker without the BIST Yahoo suffix."""
    value = (ticker or "").strip()
    if value.upper().endswith(".IS"):
        return value[:-3]
    return value

class RiskFormatter:
    """UI Formatter for Risk Profile."""
    
    _UI_PROPS = {
        RiskLabel.COK_MUHAFAZAKAR: {
            "display_name": "Cok Muhafazakar",
            "color": "#10b981", 
            "emoji": "🛡️", 
            "state": "conservative"
        },
        RiskLabel.MUHAFAZAKAR: {
            "display_name": "Muhafazakar",
            "color": "#3b82f6", 
            "emoji": "🔷", 
            "state": "moderate"
        },
        RiskLabel.DENGELI: {
            "display_name": "Dengeli",
            "color": "#f59e0b", 
            "emoji": "⚖️", 
            "state": "balanced"
        },
        RiskLabel.BUYUME_ODAKLI: {
            "display_name": "Buyume Odakli",
            "color": "#0ea5e9", 
            "emoji": "📈", 
            "state": "growth"
        },
        RiskLabel.AGRESIF: {
            "display_name": "Agresif",
            "color": "#ef4444", 
            "emoji": "🚀", 
            "state": "aggressive"
        },
    }

    @classmethod
    def get_color(cls, label: str) -> str:
        return cls._UI_PROPS.get(label, {}).get("color", "#94a3b8")

    @classmethod
    def get_emoji(cls, label: str) -> str:
        return cls._UI_PROPS.get(label, {}).get("emoji", "?")
        
    @classmethod
    def get_state(cls, label: str) -> str:
        return cls._UI_PROPS.get(label, {}).get("state", "moderate")

    @classmethod
    def get_display_name(cls, label: str) -> str:
        return cls._UI_PROPS.get(label, {}).get("display_name", label)
