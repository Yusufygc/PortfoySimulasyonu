import pytest
import os
import sys

# Testlerin 'src' modülünü kolayca görebilmesi için proje kök dizinini PYTHONPATH'e ekliyoruz.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
