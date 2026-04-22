# src/ui/core/icon_manager.py
"""
IconManager — Global İkon Servisi

SVG tabanlı ikonları yönetir, tasarım token'larına göre dinamik olarak
renklendirir ve QIcon nesneleri olarak sunar.

Kullanım:
    icon = IconManager.get_icon("plus", color="@COLOR_PRIMARY")
    button.setIcon(icon)
"""
import os
import logging
from typing import Dict, Optional
from PyQt5.QtGui import QIcon, QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtCore import QSize, Qt

logger = logging.getLogger(__name__)

class IconManager:
    _icon_cache: Dict[str, QIcon] = {}
    _svg_cache: Dict[str, str] = {}
    
    # Varsayılan ikon dizini
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ICONS_DIR = os.path.join(BASE_DIR, "assets", "icons")

    @classmethod
    def get_icon(cls, name: str, color: str = "@COLOR_TEXT_PRIMARY", size: QSize = QSize(24, 24)) -> QIcon:
        """
        Belirtilen isimdeki ikonu dinamik renk ile döner.
        
        Args:
            name: İkon adı (uzantısız, örn: 'plus')
            color: Tasarım tokenı (@COLOR_...) veya HEX kod
            size: İkon boyutu
        """
        # Cache anahtarı oluştur (isim + renk + boyut)
        cache_key = f"{name}_{color}_{size.width()}x{size.height()}"
        if cache_key in cls._icon_cache:
            return cls._icon_cache[cache_key]

        # 1. SVG içeriğini yükle
        svg_content = cls._get_svg_content(name)
        if not svg_content:
            return QIcon()

        # 2. Rengi çöz (Token -> HEX)
        hex_color = cls._resolve_color(color)

        # 3. SVG içindeki rengi değiştir
        # Lucide ikonları genellikle 'stroke="currentColor"' kullanır veya stroke değerine sahiptir
        # stroke="currentColor" yerine HEX rengi yerleştiriyoruz
        colored_svg = svg_content.replace('currentColor', hex_color)
        # Bazı SVG'lerde stroke doğrudan renk olabilir, genel bir yaklaşım için:
        if 'stroke="' in colored_svg and 'stroke="none"' not in colored_svg:
             import re
             colored_svg = re.sub(r'stroke="[^"]+"', f'stroke="{hex_color}"', colored_svg)

        # 4. SVG'yi Pixmap'e render et
        byte_data = colored_svg.encode('utf-8')
        renderer = QSvgRenderer(byte_data)
        
        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        icon = QIcon(pixmap)
        cls._icon_cache[cache_key] = icon
        return icon

    @classmethod
    def _get_svg_content(cls, name: str) -> Optional[str]:
        """SVG dosya içeriğini okur ve cache'ler."""
        if name in cls._svg_cache:
            return cls._svg_cache[name]
        
        file_path = os.path.join(cls.ICONS_DIR, f"{name}.svg")
        if not os.path.exists(file_path):
            logger.error(f"[IconManager] İkon bulunamadı: {file_path}")
            return None
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                cls._svg_cache[name] = content
                return content
        except Exception as e:
            logger.error(f"[IconManager] İkon okuma hatası ({name}): {e}")
            return None

    @classmethod
    def _resolve_color(cls, color_query: str) -> str:
        """Token referansını gerçek HEX rengine dönüştürür."""
        if not color_query.startswith("@"):
            return color_query # Zaten HEX veya isim
            
        from src.ui.styles.tokens import DEFAULT_THEME
        token_name = color_query[1:] # @ işaretini at
        color = DEFAULT_THEME.get(token_name)
        
        if not color:
            logger.warning(f"[IconManager] Bilinmeyen renk tokenı: {color_query}")
            return "#ffffff"
            
        return color

    @classmethod
    def get_icon_path(cls, name: str, color: str = "#ffffff") -> str:
        """
        İkonu renklendirir, geçici bir dosyaya yazar ve yolunu döner (QSS için).
        """
        cache_dir = os.path.join(cls.BASE_DIR, ".icon_cache")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)

        hex_color = cls._resolve_color(color)
        safe_color = hex_color.replace("#", "")
        cache_path = os.path.join(cache_dir, f"{name}_{safe_color}.svg")

        if os.path.exists(cache_path):
            return cache_path.replace("\\", "/")

        svg_content = cls._get_svg_content(name)
        if not svg_content:
            return ""

        # Renklendir
        import re
        colored_svg = svg_content.replace('currentColor', hex_color)
        if 'stroke="' in colored_svg and 'stroke="none"' not in colored_svg:
             colored_svg = re.sub(r'stroke="[^"]+"', f'stroke="{hex_color}"', colored_svg)
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(colored_svg)

        return cache_path.replace("\\", "/")

    @classmethod
    def clear_cache(cls):
        """Cache klasörünü ve hafızayı temizler."""
        cls._icon_cache.clear()
        cls._svg_cache.clear()
        cache_dir = os.path.join(cls.BASE_DIR, ".icon_cache")
        if os.path.exists(cache_dir):
            import shutil
            try:
                shutil.rmtree(cache_dir)
            except: pass
