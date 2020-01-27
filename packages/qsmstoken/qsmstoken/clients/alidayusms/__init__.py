import os
import sys
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, parent_dir)

from .services import AlidayuSMSClient
